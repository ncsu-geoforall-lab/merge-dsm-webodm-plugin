import os

import json
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

from app.plugins.views import TaskView

from worker.tasks import execute_grass_script

from app.plugins.grass_engine import grass, GrassEngineException
from geojson import Feature, Point, FeatureCollection


class TaskDSMCorrect(TaskView):
    def get(self, request, pk=None):
        print("TaskDSMCorrect")
        task = self.get_and_check_task(request, pk)
        if task.dsm_extent is None:
            return Response({'error': 'No surface model available. From the Dashboard, select this task, press Edit, from the options make sure to check "dsm", then press Restart --> From DEM.'})


        dsm = os.path.abspath(task.get_asset_download_path("dsm.tif"))

        try:
            context = grass.create_context()
            context.add_param('dsm_file', dsm)
            context.set_location(dsm)

            output = execute_grass_script.delay(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "dsm_correct.grass"
            ), context.serialize()).get()
            if isinstance(output, dict) and 'error' in output: raise GrassEngineException(output['error'])

            rows = output.split('\n')
            cols = rows[0].split('=')
            if len(cols) == 2:
                return Response({'max': str(float(cols[1]))
				}, status=status.HTTP_200_OK)
            else:
                raise GrassEngineException(output)
        except GrassEngineException as e:
            return Response({'error': str(e)}, status=status.HTTP_200_OK)



