# Copyright 2017, IBM US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns
from django.conf.urls import url

from dbaas_ui import views

urlpatterns = patterns(
    'operational_mgmt.database.views',
    # Index provides main page
    url(r'^$', views.IndexView.as_view(), name='index'),

    url(r'^launch_instance',
        views.LaunchInstanceView.as_view(), name='launch_instance'),

    url(r'^create_backup',
        views.CreateBackupView.as_view(), name='create_backup'),
    url(r'^(?P<instance_id>[^/]+)/create_backup/$',
        views.CreateBackupView.as_view(), name='create_backup'),

    url(r'^restore_from_backup',
        views.RestoreFromBackupView.as_view(), name='restore_from_backup'),

    url(r'^restart_instance',
        views.RestartInstanceView.as_view(), name='restart_instance'),
    url(r'^(?P<instance_id>[^/]+)/restart_instance/$',
        views.RestartInstanceView.as_view(), name='restart_instance'),

    url(r'^resize_instance',
        views.ResizeInstanceView.as_view(), name='resize_instance'),
    url(r'^(?P<instance_id>[^/]+)/resize_instance/$',
        views.ResizeInstanceView.as_view(), name='resize_instance'),


    url(r'^resize_volume',
        views.ResizeVolumeView.as_view(), name='resize_volume'),
    url(r'^(?P<instance_id>[^/]+)/restart_volume/$',
        views.ResizeVolumeView.as_view(), name='resize_volume'),

    url(r'^delete_instance',
        views.DeleteInstanceView.as_view(), name='delete_instance'),
    url(r'^(?P<instance_id>[^/]+)/delete_instance/$',
        views.DeleteInstanceView.as_view(), name='delete_instance'),

    url(r'^delete_backup',
        views.DeleteBackupView.as_view(), name='delete_backup'),
    url(r'^(?P<backup_id>[^/]+)/delete_backup/$',
        views.DeleteBackupView.as_view(), name='delete_backup'),)
