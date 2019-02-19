/**
 * Run ./webodm.sh restart to have webpack rebuild the file
 */


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
                if (taskInfo.max){
                    this.setState({max: parseFloat(taskInfo.max)});
                }else if (taskInfo.error){
                    this.setState({error: taskInfo.error});
                }else{
                    this.setState({error: "Invalid response: " + taskInfo});
                }
            }).fail(error => {
                this.setState({error});
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