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

    url(r'^rename_instance',
        views.RenameInstanceView.as_view(), name='rename_instance'),
    url(r'^(?P<instance_id>[^/]+)/rename_instance/$',
        views.RenameInstanceView.as_view(), name='rename_instance'),

    url(r'^delete_instance',
        views.DeleteInstanceView.as_view(), name='delete_instance'),
    url(r'^(?P<instance_id>[^/]+)/delete_instance/$',
        views.DeleteInstanceView.as_view(), name='delete_instance'),

    url(r'^delete_backup',
        views.DeleteBackupView.as_view(), name='delete_backup'),
    url(r'^(?P<backup_id>[^/]+)/delete_backup/$',
        views.DeleteBackupView.as_view(), name='delete_backup'),

    url(r'^create_user',
        views.CreateUserView.as_view(), name='create_user'),
    url(r'^(?P<instance_id>[^/]+)/create_user/$',
        views.CreateUserView.as_view(), name='create_user'),

    url(r'^delete_user',
        views.DeleteUserView.as_view(), name='delete_user'),
    url(r'^(?P<user_id>[^/]+)/delete_user/$',
        views.DeleteUserView.as_view(), name='delete_user'),

    url(r'^create_database',
        views.CreateDatabaseView.as_view(), name='create_database'),
    url(r'^(?P<instance_id>[^/]+)/create_database/$',
        views.CreateDatabaseView.as_view(), name='create_database'),

    url(r'^delete_database',
        views.DeleteDatabaseView.as_view(), name='delete_database'),
    url(r'^(?P<database_id>[^/]+)/delete_database/$',
        views.DeleteDatabaseView.as_view(), name='delete_database'),

    url(r'^(?P<instance_id>[^/]+)/manage_root/$',
        views.ManageRootView.as_view(), name='manage_root'),
    # When we have no context (no instance id) for managing root,
    # we'll call a different 'view' to prompt the user on which
    # instance to manage root.
    url(r'^manage_root',
        views.ManageRootNoContextView.as_view(), name='manage_root'),

    # URLs to details views
    url(r'^(?P<instance_id>[^/]+)/instance/$',
        views.InstanceDetailsView.as_view(), name='instance_details'),

    url(r'^(?P<backup_id>[^/]+)/backup/$',
        views.BackupDetailsView.as_view(), name='backup_details'),

)
