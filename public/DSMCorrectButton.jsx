import React from 'react';
import PropTypes from 'prop-types';
import Storage from 'webodm/classes/Storage';
import ErrorMessage from 'webodm/components/ErrorMessage';
import $ from 'jquery';

export default class DSMCorrectButton extends React.Component{
    static defaultProps = {
        task: null
    };

    static propTypes = {
        // task: PropTypes.object.isRequired
        // token: PropTypes.string.isRequired // OAM Token
    };

    constructor(props){
        super(props);

        this.state = {
            loading: true,
            taskInfo: {},
            error: ''
        };
    }

    componentDidMount(){
        
    }


    componentWillUnmount(){
        if (this.monitorTimeout) clearTimeout(this.monitorTimeout);
    }

    handleClick = () => {
        const { taskInfo } = this.state;
        console.log('DSM Correct:', this);
        const { task } = this.props;

        // const oamParams = {
        //   token: this.props.token,
        //   sensor: formData.sensor,
        //   acquisition_start: formData.startDate,
        //   acquisition_end: formData.endDate,
        //   title: formData.title,
        //   provider: formData.provider,
        //   tags: formData.tags
        // };

        return $.ajax({
            url: `/api/plugins/dsmcorrect/task/${task.id}/dsmcorrect`,
            contentType: 'application/json',
            dataType: 'json',
            type: 'GET'
          }).done(taskInfo => {
            // Allow a user to associate the sensor name coming from the EXIF tags
            // to one that perhaps is more human readable.
            // Storage.setItem("oam_sensor_pref_" + taskInfo.sensor, formData.sensor);
            // Storage.setItem("oam_provider_pref", formData.provider);

            this.setState({taskInfo});
            this.monitorProgress();
          });
    }



    monitorProgress = () => {
        if (this.state.taskInfo.sharing){
            // Monitor progress
            this.monitorTimeout = setTimeout(() => {
                this.updateTaskInfo(true).always(this.monitorProgress);
            }, 5000);
        }
    }

    render(){
        const { loading, taskInfo } = this.state;

        const getButtonIcon = () => {
            if (loading || taskInfo.sharing) return "fa fa-adjust";
            else return "fa fa-adjust";
        };

        const getButtonLabel = () => {
            if (loading) return " DSM Correct";
            else return " DSM Correct";
        }

        const result = [
                <ErrorMessage bind={[this, "error"]} />,
                <button
                onClick={this.handleClick}
                className="btn btn-sm btn-primary">
                    {[<i className={getButtonIcon()}></i>, getButtonLabel()]}
                </button>];

        if (taskInfo.sensor !== undefined){
            result.unshift(<ShareDialog 
                  ref={(domNode) => { this.shareDialog = domNode; }}
                  task={this.props.task}
                  taskInfo={taskInfo}
                  saveAction={this.shareToOAM}
                />);
        }

        return result;
    }
}

  // addActionButton(" Correct DSM", "btn-primary", "fa fa-adjust", this.genActionApiCall("dsmcorrect", {
        //   confirm: "Correct DSM. Continue?",
        //   defaultError: "Cannot complete task."
        // }));