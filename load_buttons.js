
PluginsAPI.Dashboard.addTaskActionButton([
    'rapid-dsm/build/rapid-dsm.js'
],function(args, RapidDSMButton){
    var task = args.task;

    if (task.available_assets.indexOf("orthophoto.tif") !== -1){
        return React.createElement(RapidDSMButton, {task: task});
    }
}
);
