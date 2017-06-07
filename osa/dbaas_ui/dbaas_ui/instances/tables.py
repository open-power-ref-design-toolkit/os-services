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
from django.template import defaultfilters as d_filters

from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import tables
from horizon.templatetags import sizeformat
from horizon.utils import filters

from dbaas_ui.backups.tables import BACKUPS_STATUS_CHOICES
from dbaas_ui.backups.tables import BACKUPS_STATUS_DISPLAY_CHOICES
from dbaas_ui.shortcuts import tasks

from trove_dashboard import api as trove_api

INSTANCE_STATUS_CHOICES = (
    ("ACTIVE", True),
    ("BLOCKED", True),
    ("BUILD", None),
    ("FAILED", False),
    ("REBOOT", None),
    ("RESIZE", None),
    ("BACKUP", None),
    ("SHUTDOWN", False),
    ("ERROR", False),
    ("RESTART_REQUIRED", None),
)
INSTANCE_STATUS_DISPLAY_CHOICES = (
    ("ACTIVE", pgettext_lazy("Current status of a Database Instance",
                             u"Active")),
    ("BLOCKED", pgettext_lazy("Current status of a Database Instance",
                              u"Blocked")),
    ("BUILD", pgettext_lazy("Current status of a Database Instance",
                            u"Building")),
    ("FAILED", pgettext_lazy("Current status of a Database Instance",
                             u"Failed")),
    ("REBOOT", pgettext_lazy("Current status of a Database Instance",
                             u"Rebooting")),
    ("RESIZE", pgettext_lazy("Current status of a Database Instance",
                             u"Resizing")),
    ("BACKUP", pgettext_lazy("Current status of a Database Instance",
                             u"Backup")),
    ("SHUTDOWN", pgettext_lazy("Current status of a Database Instance",
                               u"Shutdown")),
    ("ERROR", pgettext_lazy("Current status of a Database Instance",
                            u"Error")),
    ("RESTART_REQUIRED",
     pgettext_lazy("Current status of a Database Instance",
                   u"Restart Required")),
)


class UpdateRowInstances(tables.Row):
    ajax = True

    def get_data(self, request, instance_id):
        instance = trove_api.trove.instance_get(request, instance_id)
        try:
            flavor_id = instance.flavor['id']
            instance.full_flavor = trove_api.trove.flavor_get(request,
                                                              flavor_id)
        except Exception:
            pass
        instance.host = get_host(instance)
        return instance


def get_host(instance):
    if hasattr(instance, "hostname"):
        return instance.hostname
    elif hasattr(instance, "ip") and instance.ip:
        return instance.ip[0]
    return _("Not Assigned")


def get_datastore(instance):
    if hasattr(instance, "datastore"):
        return instance.datastore["type"]
    return _("Not available")


def get_datastore_version(instance):
    if hasattr(instance, "datastore"):
        return instance.datastore["version"]
    return _("Not available")


def get_size(instance):
    if hasattr(instance, "full_flavor"):
        size_string = _("%(name)s | %(RAM)s RAM")
        vals = {'name': instance.full_flavor.name,
                'RAM': sizeformat.mb_float_format(instance.full_flavor.ram)}
        return size_string % vals
    return _("Not available")


def get_volume_size(instance):
    if hasattr(instance, "volume"):
        return sizeformat.diskgbformat(instance.volume.get("size"))
    return _("Not available")


def get_databases(user):
    if hasattr(user, "access"):
        databases = [db.name for db in user.access]
        databases.sort()
        return ', '.join(databases)
    return _("-")


def db_name(obj):
    # TODO(jdwald):  Investigate -- if the backup doesn't have an instance or
    #        it has an instance, but the instance does not have a name
    #        then return the instance ID -- which is not very useful...
    if not hasattr(obj, 'instance') or not hasattr(obj.instance, 'name'):
        return obj.instance_id
    return obj.instance.name


def is_incremental(obj):
    return hasattr(obj, 'parent_id') and obj.parent_id is not None


class UsersTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("User Name"))
    # host = tables.Column("host", verbose_name=_("Allowed Host"))
    databases = tables.Column(get_databases, verbose_name=_("Databases"))

    class Meta(object):
        name = "users"
        verbose_name = _("Users")
        table_actions = (tasks.CreateUserLink, tasks.GenericFilterAction,)
        row_actions = (tasks.ManageUserDBAccess, tasks.DeleteUserLink,)

    def get_object_id(self, datum):
        return datum.name


class DatabaseTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Database Name"))

    class Meta(object):
        name = "databases"
        verbose_name = _("Databases")
        table_actions = (tasks.CreateDatabaseLink, tasks.GenericFilterAction,)
        row_actions = (tasks.DeleteDatabaseLink,)

    def get_object_id(self, datum):
        return datum.name


class InstanceBackupsTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:dbaas_ui:backups:detail",
                         verbose_name=_("Name"))
    created = tables.Column("created", verbose_name=_("Created"),
                            filters=[filters.parse_isotime])
    location = tables.Column(lambda obj: _("Download"),
                             link=lambda obj: obj.locationRef,
                             verbose_name=_("Backup File"))
    incremental = tables.Column(is_incremental,
                                verbose_name=_("Incremental"),
                                filters=(d_filters.yesno,
                                         d_filters.capfirst))

    # TODO(jdwald):  Need some investigation.  Due to tabbed interface,
    #                the dynamic update of the status column is not working.
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=BACKUPS_STATUS_CHOICES,
                           display_choices=BACKUPS_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "backups"
        verbose_name = _("Backups")
        status_columns = ["status"]
        table_actions = (tasks.GenericFilterAction, tasks.CreateBackupLink)
        row_actions = (tasks.RestoreFromBackupLink, tasks.DeleteBackupLink,)


class InstancesTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:dbaas_ui:instances:detail",
                         verbose_name=_("Instance Name"))
    datastore = tables.Column(get_datastore,
                              verbose_name=_("Datastore"))
    datastore_version = tables.Column(get_datastore_version,
                                      verbose_name=_("Datastore Version"))
    host = tables.Column(get_host, verbose_name=_("Host"))
    size = tables.Column(get_size,
                         verbose_name=_("Size"),
                         attrs={'data-type': 'size'})
    volume = tables.Column(get_volume_size,
                           verbose_name=_("Volume Size"),
                           attrs={'data-type': 'size'})
    # TODO(jdwald):  Need some investigation.  Due to tabbed interface,
    #                the dynamic update of the status column is not working.
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=INSTANCE_STATUS_CHOICES,
                           display_choices=INSTANCE_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "instances"
        verbose_name = _("Instances")
        status_columns = ["status"]
        row_class = UpdateRowInstances
        table_actions = (tasks.LaunchInstanceLink, tasks.GenericFilterAction)
        row_actions = (tasks.CreateBackupLink,
                       tasks.RenameInstanceLink,
                       tasks.ResizeInstanceLink,
                       tasks.ResizeVolumeLink,
                       tasks.RestartInstanceLink,
                       # tasks.UpgradeInstanceLink,
                       tasks.ManageRootLink,
                       tasks.DeleteInstanceLink,)
