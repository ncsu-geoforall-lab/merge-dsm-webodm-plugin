#%module
#% description: Calculate volume of area and prints the volume to stdout
#%end
#%option
#% key: area_file
#% type: string
#% required: yes
#% multiple: no
#% description: Geospatial file containing the area to measure
#%end
#%option
#% key: points_file
#% type: string
#% required: yes
#% multiple: no
#% description: Geospatial file containing the points defining the area
#%end
#%option
#% key: dsm_file
#% type: string
#% required: yes
#% multiple: no
#% description: GeoTIFF DEM containing the surface
#%end

import os
import sys
import atexit
import grass.script as gs
import grass.script.array as garray
from sklearn.mixture import BayesianGaussianMixture as GMM
import numpy as np
from grass.pygrass.modules import Module


TMP_RAST = []
TMP_VECT = []
stddev_thr = 5
mean_thr = 2


def import_dsm(output, output_dir, input_srs, resolution, nprocs):
    gs.run_command(
        "r.in.usgs",
        product="lidar",
        output_name=output,
        output_directory=output_dir,
        input_srs=input_srs,
        resolution=resolution,
        nprocs=nprocs,
        flags="k",
    )


def import_dem(output, output_dir, nprocs):
    gs.run_command(
        "r.in.usgs",
        product="ned",
        ned_dataset="ned19sec",
        output_name=output,
        output_directory=output_dir,
        nprocs=nprocs,
    )


def resample(uas, dem, match_uas=True):
    # resample uas to match lidar, or the other way round?
    resampled = "tmp_resampled"
    uas_ = uas
    dem_ = dem

    if not match_uas:
        gs.run_command("g.region", raster=uas, align=dem)
        gs.run_command("r.resamp.interp", input=uas, output=resampled)
        uas_ = resampled
    else:
        gs.run_command("g.region", raster=dem, align=uas)
        gs.run_command("r.resamp.interp", input=dem, output=resampled)
        dem_ = resampled

    TMP_RAST.append(resampled)
    return uas_, dem_


def get_diff(uas, dem, mean_thr):
    # compute difference
    diff = "tmp_diff"
    gs.run_command("g.region", raster=uas)
    gs.mapcalc(diff + " = " + uas + " - " + dem)
    TMP_RAST.append(diff)
    univar = gs.parse_command("r.univar", map=diff, flags="ge")
    mean = float(univar["mean"])
    stddev = float(univar["stddev"])

    print("Difference: {mean:.1f} ± {stddev:.1f}".format(mean=mean, stddev=stddev))
    # test for systematic shift:
    if abs(mean) > mean_thr:
        gs.warning("Vertical shift is likely.")
    return diff, mean


def vertically_corrected_uas(uas, dem, shift):
    new = "vertically_corrected"
    diff = "tmp_diff_corrected"
    gs.mapcalc("{new} = {uas} - {shift}".format(shift=shift, uas=uas, new=new))
    TMP_RAST.append(new)
    gs.mapcalc(diff + " = " + new + " - " + dem)
    TMP_RAST.append(diff)

    return new, diff


def gmm(diff):
    gs.run_command("g.region", raster=diff)
    diff_values = garray.array(mapname=diff)
    diff_values = diff_values.flatten()
    diff_values = diff_values[diff_values != 0]
    X = diff_values.reshape(-1, 1)
    gmm = GMM(n_components=2).fit(X)
    means = gmm.means_.flatten()
    stddevs = np.sqrt(gmm.covariances_).flatten()
    weights = gmm.weights_
    gs.message(
        "GMM means: {m}, stddev: {s}, weights: {w}".format(
            m=means, s=stddevs, w=weights
        )
    )
    # lot of changes between uas and dem
    if abs(weights[1] - weights[0]) < 0.3 and abs(means[1] - means[0]) < 2 * mean_thr:
        idx = np.argmin(stddevs)
    else:
        idx = np.argmax(weights)
    gs.message("Selected index: " + str(idx))

    mean = means[idx]
    stddev = stddevs[idx]
    return mean, stddev


def distort(uas, diff, mean, stddev):
    range_map = "tmp_range"
    gs.run_command(
        "r.neighbors", flags="c", input=diff, output=range_map, method="range", size=5
    )
    TMP_RAST.append(range_map)

    stable_diff = "tmp_diff_stable"
    interp = "tmp_interpolated"
    sample = "tmp_sample"
    stddev_multipl = 2
    rangev = (-stddev_multipl * stddev, stddev_multipl * stddev)
    gs.mapcalc(
        "{sd} = if ({r} < 1 && {diff} > {thr0} && {diff} < {thr1}, {diff}, null())".format(
            sd=stable_diff, r=range_map, diff=diff, thr1=rangev[1], thr0=rangev[0]
        )
    )
    TMP_RAST.append(stable_diff)
    gs.run_command(
        "r.random",
        flags="db",
        input=stable_diff,
        cover=stable_diff,
        npoints=100,
        vector=sample,
    )
    TMP_VECT.append(sample)

    gs.run_command(
        "v.surf.rst", input=sample, elevation=interp, mask=uas, tension=20, smooth=1
    )
    TMP_RAST.append(interp)

    corrected = "tmp_corrected"
    gs.mapcalc("{c}= {o} - {i}".format(c=corrected, o=uas, i=interp))
    TMP_RAST.append(corrected)
    return corrected


def patch(uas, dem, output):
    gs.run_command("g.region", raster=dem)
    gs.run_command(
        "r.patch.smooth", input_a=uas, input_b=dem, output=output, smooth_dist=10
    )
    gs.run_command("r.colors", map=[output, dem, uas], color="elevation")


def cleanup():
    gs.run_command(
        "g.remove", flags="f", type="raster", name=",".join(TMP_RAST), quiet=True
    )
    gs.run_command(
        "g.remove", flags="f", type="vector", name=",".join(TMP_VECT), quiet=True
    )


def main(uas, dem, output, buffer):
    gs.run_command("g.region", raster=uas)
    uas_reg = gs.region(uas)
    avg_wh = ((uas_reg["n"] - uas_reg["s"]) + (uas_reg["e"] - uas_reg["w"])) / 2.0
    n = uas_reg["n"] + avg_wh * buffer
    s = uas_reg["s"] - avg_wh * buffer
    e = uas_reg["e"] + avg_wh * buffer
    w = uas_reg["w"] - avg_wh * buffer
    gs.run_command("g.region", n=n, e=e, s=s, w=w)
    import_dsm(dem, output_dir='/tmp', input_srs='EPSG:2264', resolution=3, nprocs=4)
    #import_dem(dem, '/tmp/',  nprocs=4)
    gs.use_temp_region()
    uas, dem = resample(uas, dem, True)
    diff, univar_shift = get_diff(uas, dem, 2)
    gmm_mean, gmm_stddev = gmm(diff)
    uas, diff = vertically_corrected_uas(uas, dem, gmm_mean)
    uas = distort(uas, diff, gmm_mean, gmm_stddev)
    patch(uas, dem, output)

    gs.del_temp_region()


if __name__ == "__main__":
    os.environ["GRASS_OVERWRITE"] = "1"
    #Load DSM data from WebODM
    gs.run_command("r.external", input=opts['dsm_file'], output="uav", overwrite=True)
    uas_dsm = "uav"
    lidar_dsm = "lidar"
    lidar_dem = "ned"
    dem = lidar_dsm
    output = "fused"
    buffer = 0.5
    atexit.register(cleanup)
    sys.exit(main(uas_dsm, dem, output, buffer))


# def main():

   
    # Import raster
    # Module("r.external", input=opts['dsm_file'], output="dsm", overwrite=True)
    # Module("v.import", input=opts['area_file'], output="polygon_area", overwrite=True)
    # Module("v.import", input=opts['points_file'], output="polygon_points", overwrite=True)
    # Module("v.buffer", input="polygon_area", s=True, type="area", output="region", distance=1, minordistance=1, overwrite=True)

    # # Set Grass region and resolution to DSM
    # Module("g.region", raster="dsm") 
    
    # # Set Grass region to vector bbox
    # Module("g.region", vector="region")

    # # Create a mask to speed up computation
    # Module("r.mask", vector="region")

    # # Transfer dsm raster data to vector
    # Module("v.what.rast", map="polygon_points", raster="dsm", column="height")

    # # Decimate DSM and generate interpolation of new terrain
    # Module("v.surf.rst", input="polygon_points", zcolumn="height", elevation="dsm_below_pile", overwrite=True)

    # # Compute difference between dsm and new dsm
    # Module("r.mapcalc", expression='pile_height_above_dsm=dsm-dsm_below_pile', overwrite=True)

    # # Set region to polygon area to calculate volume
    # Module("g.region", vector="polygon_area")

    # # Volume output from difference
    # Module("r.volume", input="pile_height_above_dsm", f=True)

#     return 0

# if __name__ == "__main__":
#     opts, _ = grass.parser()
#     sys.exit(main())
