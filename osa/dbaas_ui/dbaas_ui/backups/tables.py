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
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon.utils import filters

from dbaas_ui.shortcuts import tasks

from trove_dashboard import api as trove_api

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


class DeleteBackup(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Backup",
            u"Delete Backups",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Backup",
            u"Deleted Backups",
            count
        )

    def delete(self, request, obj_id):
        trove_api.trove.backup_delete(request, obj_id)


class LaunchLink(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Backup")
    url = "horizon:dbaas_ui:shortcuts:create_backup"
    classes = ("ajax-modal", "btn-create")
    icon = "camera"


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


def get_datastore(instance):
    if hasattr(instance, "datastore"):
        return instance.datastore["type"]
    return _("Not available")


def get_datastore_version(instance):
    if hasattr(instance, "datastore"):
        return instance.datastore["version"]
    return _("Not available")


def is_incremental(obj):
    return hasattr(obj, 'parent_id') and obj.parent_id is not None


class BackupsTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:dbaas_ui:backups:detail",
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

    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=BACKUPS_STATUS_CHOICES,
                           display_choices=BACKUPS_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "backups"
        verbose_name = _("Backups")
        status_columns = ["status"]
        row_class = UpdateRowBackups
        table_actions = (tasks.GenericFilterAction, LaunchLink,
                         DeleteBackup)
        row_actions = (tasks.RestoreFromBackupLink, tasks.DeleteBackupLink)
