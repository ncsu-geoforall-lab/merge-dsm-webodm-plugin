
PluginsAPI.Dashboard.addTaskActionButton([
    'merge_dsm_webodm_plugin/build/DSMCorrectButton.js'
],function(args, DSMCorrectButton){
    var task = args.task;

    if (task.available_assets.indexOf("orthophoto.tif") !== -1){
        return React.createElement(DSMCorrectButton, {task: task});
    }
}
);
