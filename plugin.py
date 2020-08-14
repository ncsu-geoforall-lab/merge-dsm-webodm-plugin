from django.contrib import messages
from django.shortcuts import render

from app.plugins import PluginBase, MountPoint
from django.contrib.auth.decorators import login_required
from django import forms

from .api import TaskRapidDSM


class Plugin(PluginBase):

    def include_js_files(self):
        return ['main.js']

    def build_jsx_components(self):
        return ['rapid-dsm.jsx']

    def include_css_files(self):
        return ['style.css']

    def app_mount_points(self):
        return [
            MountPoint('main.js$', self.get_dynamic_script(
                    'load_buttons.js'
                )
            )
        ]    

    def api_mount_points(self):
        return [
            MountPoint('task/(?P<pk>[^/.]+)/rapid-dsm', TaskRapidDSM.as_view())
        ]