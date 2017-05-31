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
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import defaultfilters as d_filters

from django.utils import http
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import messages
from horizon import tables
from horizon.templatetags import sizeformat
from horizon.utils import filters

import six.moves.urllib.parse as urlparse

from trove_dashboard import api as trove_api


import logging

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

"""
class UpgradeInstanceLink(tables.LinkAction):
    name = "upgradeInstance"
    verbose_name = _("Upgrade Instance")
    url = "horizon:project:database:upgrade_instance"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE' or
                instance.status == 'SHUTOFF')
"""


class DeleteInstanceLink(tables.LinkAction):
    # Always allowed in table of instances
    name = "deleteInstance"
    verbose_name = _("Delete")
    url = "horizon:project:database:delete_instance"
    classes = ("ajax-modal", "btn-danger")
    icon = "trash"


class CreateUserLink(tables.LinkAction):
    name = "create_user"
    verbose_name = _("Create User")
    url = "horizon:project:database:create_user"
    verbose_name = _("Create User")
    classes = ("ajax-modal", "btn-create")
    icon = "plus"

    def allowed(self, request, instance=None):
        if (instance):
            return (instance and instance.status in 'ACTIVE' and
                    has_user_add_perm(request))
        else:
            return has_user_add_perm(request)

    def get_link_url(self):
        if 'instance_id' in self.table.kwargs:
            instance_id = self.table.kwargs['instance_id']
            url = reverse(self.url, args=[instance_id])
        else:
            url = reverse(self.url)
        return url


class CreateBackupLink(tables.LinkAction):
    name = "create"
    url = "horizon:project:database:create_backup"
    verbose_name = _("Create Backup")
    classes = ("ajax-modal", "btn-create")
    icon = "camera"

    def allowed(self, request, instance=None):
        if (instance):
            return (instance and instance.status in 'ACTIVE' and
                    request.user.has_perm('openstack.services.object-store'))
        else:
            return request.user.has_perm('openstack.services.object-store')

    def get_link_url(self, datum=None):
        instance_id = None
        if 'instance_id' in self.table.kwargs:
            instance_id = self.table.kwargs['instance_id']
        else:
            instance_id = self.table.get_object_id(datum)

        if instance_id:
            url = reverse(self.url, args=[instance_id])
        else:
            url = reverse(self.url)
        return url


class CreateDatabaseLink(tables.LinkAction):
    name = "create_database"
    url = "horizon:project:database:create_database"
    verbose_name = _("Create Database")
    classes = ("ajax-modal", "btn-create")
    icon = "plus"

    def allowed(self, request, database=None):
        instance = self.table.kwargs['instance']
        return (instance.status in 'ACTIVE' and
                has_database_add_perm(request))

    def get_link_url(self):
        if 'instance_id' in self.table.kwargs:
            instance_id = self.table.kwargs['instance_id']
            url = reverse(self.url, args=[instance_id])
        else:
            url = reverse(self.url)
        return url


def has_database_add_perm(request):
    perms = getattr(settings, 'TROVE_ADD_DATABASE_PERMS', [])
    if perms:
        return request.user.has_perms(perms)
    return True


class DeleteBackupLink(tables.LinkAction):
    # Always allowed in table of backups
    name = "deleteBackup"
    verbose_name = _("Delete")
    url = "horizon:project:database:delete_backup"
    classes = ("ajax-modal", "btn-danger")
    icon = "trash"


class DeleteUserLink(tables.LinkAction):
    # Always allowed in table of users
    name = "deleteUser"
    verbose_name = _("Delete")
    url = "horizon:project:database:delete_user"
    classes = ("ajax-modal", "btn-danger")
    icon = "trash"

    def get_link_url(self, datum):
        if 'instance_id' in self.table.kwargs:
            # we need both the instance ID and the name of the user to delete
            instance_id = self.table.kwargs['instance_id'] + "::" + datum.name
            url = reverse(self.url, args=[instance_id])
        else:
            url = reverse(self.url)
        return url


class DeleteDatabaseLink(tables.LinkAction):
    # Always allowed in table of databases
    name = "deleteDatabase"
    verbose_name = _("Delete")
    url = "horizon:project:database:delete_database"
    classes = ("ajax-modal", "btn-danger")
    icon = "trash"

    def get_link_url(self, datum):
        if 'instance_id' in self.table.kwargs:
            # we need both the instance ID and the name of the user to delete
            instance_id = self.table.kwargs['instance_id'] + "::" + datum.name
            url = reverse(self.url, args=[instance_id])
        else:
            url = reverse(self.url)
        return url


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


def parse_host_param(request):
    # Retrieve the host from the request
    host = None
    if request.META.get('QUERY_STRING', ''):
        param = urlparse.parse_qs(request.META.get('QUERY_STRING'))
        values = param.get('host')
        if values:
            host = next(iter(values), None)
    return host


class GrantDBAccess(tables.BatchAction):
    # Allowed when the database indicates the user has no access
    # to the database.  This function grants the user access to the
    # database.
    # Note that this action requires no end-user interaction -- once
    # the user selects this table action, it just runs.
    name = "grant_access"
    classes = ('btn-grant-access')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Grant Access",
            u"Grant Access",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Granted Access to",
            u"Granted Access to",
            count
        )

    def allowed(self, request, instance=None):
        if instance:
            return not instance.access
        return False

    def action(self, request, obj_id):
        trove_api.trove.user_grant_access(
            request,
            self.table.kwargs['instance_id'],
            self.table.kwargs['user_name'],
            [obj_id],
            host=parse_host_param(request))


class RevokeDBAccess(tables.BatchAction):
    # Allowed when the database indicates the user has access to the database.
    # This function revokes the user access to the database on the
    # instance.
    # Note that this action requires no end-user interaction -- once the
    # user selects this table action, it just runs.
    name = "revoke_access"
    classes = ('btn-revoke-access')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Revoke Access",
            u"Revoke Access",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Access Revoked to",
            u"Access Revoked to",
            count
        )

    def allowed(self, request, instance=None):
        if instance:
            return instance.access
        return False

    def action(self, request, obj_id):
        trove_api.trove.user_revoke_access(
            request,
            self.table.kwargs['instance_id'],
            self.table.kwargs['user_name'],
            obj_id,
            host=parse_host_param(request))


class ManageUserDBAccess(tables.LinkAction):
    name = "manage_user_db_access"
    verbose_name = _("Manage Access")
    url = "horizon:project:database:manage_user"
    icon = "pencil"

    def allowed(self, request, instance=None):
        instance = self.table.kwargs['instance']
        return (instance and instance.status in 'ACTIVE' and
                has_user_add_perm(request))

    def get_link_url(self, datum):
        user = datum
        url = reverse(self.url, args=[user.instance.id,
                                      user.name])
        if user.host:
            params = http.urlencode({"host": user.host})
            url = "?".join([url, params])

        return url


class ManageRootLink(tables.LinkAction):
    # Allowed on instances that are active.  This function opens
    # the Manage Root Access table.  From that table a flag shows
    # if the superuser has ever been enabled, and the user can
    # enable root, disable root, or reset the root password.
    name = "manage_root_action"
    verbose_name = _("Manage Root Access")
    url = "horizon:project:database:manage_root"

    def allowed(self, request, instance):
        if (instance):
            return (instance and instance.status in 'ACTIVE')
        else:
            return True

    def get_link_url(self, datum=None):
        instance_id = self.table.get_object_id(datum)
        return reverse(self.url, args=[instance_id])


class EnableRootAction(tables.Action):
    # Always allowed in Manage Root Access table.  This function
    # enables the superuser profile (root) on the selected
    # instance if it has never been enabled, and it generates
    # a new password for the profile.  If root has already been
    # enabled on the instance, the function simply creates a new
    # password for root.  In either case, the table is updated with
    # the new password for root (so it can be viewed by the end-user)
    # Note that this action requires no end-user interaction -- once
    # the user selects this table action, it just runs.
    name = "enable_root_action"
    verbose_name = _("Enable Root")

    def handle(self, table, request, obj_ids):
        __method__ = "tables.EnableRootAction.handle"
        try:
            username, password = trove_api.trove.root_enable(request, obj_ids)
            # Once root has been enabled, update the table accordingly
            # with the enabled flag and password
            table.data[0].enabled = True
            table.data[0].password = password
        except Exception as e:
            logging.error("%s: Exception trying to enable root on %s.  "
                          "Exception: %s", __method__, obj_ids, e)
            messages.error(request, _('There was a problem enabling '
                                      'root: %s') % e.message)


class DisableRootAction(tables.Action):
    # Allowed when root has been enabled.  This function scrambles
    # the superuser profile (root) -- rendering the profile disabled (root
    # is unable to access the instance since the password is not known).
    # Note that this action requires no end-user interaction -- once the
    # user selects this table action, it just runs.
    name = "disable_root_action"
    verbose_name = _("Disable Root")

    def allowed(self, request, instance):
        enabled = trove_api.trove.root_show(request, instance.id)
        return enabled.rootEnabled

    # multi-select is not supported
    def single(self, table, request, object_id):
        __method__ = "tables.DisableRootAction.single"
        try:
            # This API merely sets the root password to
            # a random password.
            trove_api.trove.root_disable(request, object_id)
            table.data[0].password = None
            messages.success(request, _("Successfully disabled root access."))
        except Exception as e:
            logging.error("%s: Exception trying to disable root on %s.  "
                          "Exception: %s", __method__, object_id, e)
            messages.warning(request,
                             _("There was a problem enabling "
                               "root: %s") % e.message)


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


def get_databases(user):
    if hasattr(user, "access"):
        databases = [db.name for db in user.access]
        databases.sort()
        return ', '.join(databases)
    return _("-")


def db_link(obj):
    if not hasattr(obj, 'instance'):
        return
    if hasattr(obj.instance, 'name'):
        return reverse(
            'horizon:project:databases:detail',
            kwargs={'instance_id': obj.instance_id})


def db_name(obj):
    # TODO(jdwald):  Investigate -- if the backup doesn't have an instance or
    #        it has an instance, but the instance does not have a name
    #        then return the instance ID -- which is not very useful...
    if not hasattr(obj, 'instance') or not hasattr(obj.instance, 'name'):
        return obj.instance_id
    return obj.instance.name


def is_incremental(obj):
    return hasattr(obj, 'parent_id') and obj.parent_id is not None


def has_user_add_perm(request):
    perms = getattr(settings, 'TROVE_ADD_USER_PERMS', [])
    if perms:
        return request.user.has_perms(perms)
    return True


class InstancesTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:project:database:instance_details",
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
        # row_class = UpdateRowInstances
        table_actions = (LaunchInstanceLink, GenericFilterAction)
        row_actions = (CreateBackupLink,
                       RenameInstanceLink,
                       ResizeInstanceLink,
                       ResizeVolumeLink,
                       RestartInstanceLink,
                       # UpgradeInstanceLink,
                       ManageRootLink,
                       DeleteInstanceLink,)


class BackupsTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:project:database:backup_details",
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
        # row_class = UpdateRowBackups
        table_actions = (GenericFilterAction, CreateBackupLink)
        row_actions = (RestoreFromBackupLink, DeleteBackupLink,)


class UsersTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("User Name"))
    # host = tables.Column("host", verbose_name=_("Allowed Host"))
    databases = tables.Column(get_databases, verbose_name=_("Databases"))

    class Meta(object):
        name = "users"
        verbose_name = _("Users")
        table_actions = (CreateUserLink, GenericFilterAction,)
        row_actions = (ManageUserDBAccess, DeleteUserLink,)

    def get_object_id(self, datum):
        return datum.name


class DatabaseTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Database Name"))

    class Meta(object):
        name = "databases"
        verbose_name = _("Databases")
        table_actions = (CreateDatabaseLink, GenericFilterAction,)
        row_actions = (DeleteDatabaseLink,)

    def get_object_id(self, datum):
        return datum.name


class ManageRootTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Instance Name'))
    enabled = tables.Column('enabled',
                            verbose_name=_('Has Root Ever Been Enabled'),
                            filters=(d_filters.yesno, d_filters.capfirst),
                            help_text=_("Status if root was ever enabled "
                                        "for an instance."))
    password = tables.Column('password', verbose_name=_('Password'),
                             help_text=_("Password is only visible "
                                         "immediately after the root is "
                                         "enabled or reset."))

    class Meta(object):
        name = "manage_root"
        verbose_name = _("Manage Root")
        row_actions = (EnableRootAction, DisableRootAction,)


class ManageUserDBTable(tables.DataTable):
    dbname = tables.Column("name", verbose_name=_("Database Name"))
    access = tables.Column(
        "access",
        verbose_name=_("Accessible"),
        filters=(d_filters.yesno, d_filters.capfirst))

    class Meta(object):
        name = "access"
        verbose_name = _("Database Access")
        row_actions = (GrantDBAccess, RevokeDBAccess)

    def get_object_id(self, datum):
        return datum.name


class InstanceBackupsTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:project:database:backup_details",
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
        table_actions = (GenericFilterAction, CreateBackupLink)
        row_actions = (RestoreFromBackupLink, DeleteBackupLink,)
