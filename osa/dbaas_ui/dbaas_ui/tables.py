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
from django.core.urlresolvers import reverse
from django.template import defaultfilters as d_filters

from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import tables
from horizon.templatetags import sizeformat
from horizon.utils import filters
from openstack_dashboard import api as trove_api

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

BACKUPS_STATUS_CHOICES = (
    ("BUILDING", None),
    ("COMPLETED", True),
    ("DELETE_FAILED", False),
    ("FAILED", False),
    ("NEW", None),
    ("SAVING", None),
)
BACKUPS_STATUS_DISPLAY_CHOICES = (
    ("BUILDING", pgettext_lazy("Current status of a Database Backup",
                               u"Building")),
    ("COMPLETED", pgettext_lazy("Current status of a Database Backup",
                                u"Completed")),
    ("DELETE_FAILED", pgettext_lazy("Current status of a Database Backup",
                                    u"Delete Failed")),
    ("FAILED", pgettext_lazy("Current status of a Database Backup",
                             u"Failed")),
    ("NEW", pgettext_lazy("Current status of a Database Backup",
                          u"New")),
    ("SAVING", pgettext_lazy("Current status of a Database Backup",
                             u"Saving")),
)


#######################################################
#
#   START OF TASKS
#
#######################################################

#  Start of Instance-related tasks
class LaunchInstanceLink(tables.LinkAction):
    name = "launch"
    url = "horizon:project:database:launch_instance"
    verbose_name = _("Launch Instance")
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"


class RestartInstanceLink(tables.LinkAction):
    name = "restartInstance"
    verbose_name = _("Restart")
    url = "horizon:project:database:restart_instance"
    classes = ("ajax-modal",)
    icon = "refresh"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE' or
                instance.status == 'SHUTDOWN' or
                instance.status == 'RESTART_REQUIRED')


class ResizeInstanceLink(tables.LinkAction):
    name = "resizeInstance"
    verbose_name = _("Resize Instance")
    url = "horizon:project:database:resize_instance"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE' or
                instance.status == 'SHUTOFF')


class RenameInstanceLink(tables.LinkAction):
    name = "renameInstance"
    verbose_name = _("Rename Instance")
    url = "horizon:project:database:rename_instance"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"


class ResizeVolumeLink(tables.LinkAction):
    name = "resizeVolume"
    verbose_name = _("Resize Volume")
    url = "horizon:project:database:resize_volume"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE')


class DeleteInstanceLink(tables.LinkAction):
    # Always allowed in table of instances
    name = "deleteInstance"
    verbose_name = _("Delete")
    url = "horizon:project:database:delete_instance"
    classes = ("ajax-modal",)
    icon = "trash"


class CreateBackupLink(tables.LinkAction):
    name = "create"
    url = "horizon:project:database:create_backup"
    verbose_name = _("Create Backup")
    classes = ("ajax-modal", "btn-create")
    icon = "camera"

    def allowed(self, request, instance=None):
        return (instance and instance.status in 'ACTIVE' and
                request.user.has_perm('openstack.services.object-store'))

#  Start of Backups-related tasks


class DeleteBackupLink(tables.LinkAction):
    # Always allowed in table of backups
    name = "deleteBackup"
    verbose_name = _("Delete")
    url = "horizon:project:database:delete_backup"
    classes = ("ajax-modal",)
    icon = "trash"


class RestoreFromBackupLink(tables.LinkAction):
    name = "restore"
    verbose_name = _("Restore Backup")
    url = "horizon:project:database:restore_from_backup"
    classes = ("ajax-modal",)
    icon = "cloud-upload"

    def allowed(self, request, backup=None):
        return backup.status == 'COMPLETED'

    def get_link_url(self, datum):
        url = reverse(self.url)
        return url + '?backup=%s' % datum.id

# Start of other tasks


class GenericFilterAction(tables.FilterAction):
    name = "generic_filter"

    def filter(self, table, elements, filter_string):
        """Naive case-insensitive search."""
        q = filter_string.lower()
        return [element for element in elements
                if q in element.name.lower()]

#######################################################
#
#   END OF TASKS
#
#######################################################


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


class UpdateRowBackups(tables.Row):
    ajax = True

    def get_data(self, request, backup_id):
        backup = trove_api.trove.backup_get(request, backup_id)
        try:
            backup.instance = trove_api.trove.instance_get(request,
                                                           backup.instance_id)
        except Exception:
            pass
        return backup


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


def db_link(obj):
    if not hasattr(obj, 'instance'):
        return
    if hasattr(obj.instance, 'name'):
        return reverse(
            'horizon:project:databases:detail',
            kwargs={'instance_id': obj.instance_id})


def db_name(obj):
    # TODO:  Investigate -- if the backup doesn't have an instance or
    #        it has an instance, but the instance does not have a name
    #        then return the instance ID -- which is not very useful...
    if not hasattr(obj, 'instance') or not hasattr(obj.instance, 'name'):
        return obj.instance_id
    return obj.instance.name


def is_incremental(obj):
    return hasattr(obj, 'parent_id') and obj.parent_id is not None


class InstancesTable(tables.DataTable):
    # Currently details for backups is not yet available.  When it is,
    # add:  link="xxxxx:detail"
    name = tables.Column("name",
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
    # TODO:  Need some investigation.  Due to tabbed interface, the dynamic
    #        update of the status column is not working.
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=INSTANCE_STATUS_CHOICES,
                           display_choices=INSTANCE_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "instances"
        verbose_name = _("Instances")
        status_columns = ["status"]
        # row_class = UpdateRowInstances
        table_actions = (LaunchInstanceLink, GenericFilterAction)
        row_actions = (CreateBackupLink,
                       RenameInstanceLink,
                       ResizeInstanceLink,
                       ResizeVolumeLink,
                       RestartInstanceLink,
                       DeleteInstanceLink,)


class BackupsTable(tables.DataTable):
    # Currently details for backups is not yet available.  When it is,
    # add:  link="xxxxx:detail"
    name = tables.Column("name",
                         verbose_name=_("Name"))
    datastore = tables.Column(get_datastore,
                              verbose_name=_("Datastore"))
    datastore_version = tables.Column(get_datastore_version,
                                      verbose_name=_("Datastore Version"))
    created = tables.Column("created", verbose_name=_("Created"),
                            filters=[filters.parse_isotime])
    # Based on discussions with UX designer, remove the db instance
    # column and have that information placed on details panel.
    # instance = tables.Column(db_name, link=db_link,
    #                         verbose_name=_("Database"))

    incremental = tables.Column(is_incremental,
                                verbose_name=_("Incremental"),
                                filters=(d_filters.yesno,
                                         d_filters.capfirst))
    # TODO:  Need some investigation.  Due to tabbed interface, the dynamic
    #        update of the status column is not working.
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=BACKUPS_STATUS_CHOICES,
                           display_choices=BACKUPS_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "backups"
        verbose_name = _("Backups")
        status_columns = ["status"]
        # row_class = UpdateRowBackups
        table_actions = (GenericFilterAction, CreateBackupLink)
        row_actions = (RestoreFromBackupLink, DeleteBackupLink,)
