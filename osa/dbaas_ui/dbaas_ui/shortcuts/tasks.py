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

from django.utils import http
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import messages
from horizon import tables

import six.moves.urllib.parse as urlparse

from trove_dashboard import api as trove_api


import logging


def has_user_add_perm(request):
    perms = getattr(settings, 'TROVE_ADD_USER_PERMS', [])
    if perms:
        return request.user.has_perms(perms)
    return True


def has_database_add_perm(request):
    perms = getattr(settings, 'TROVE_ADD_DATABASE_PERMS', [])
    if perms:
        return request.user.has_perms(perms)
    return True


def parse_host_param(request):
    # Retrieve the host from the request
    host = None
    if request.META.get('QUERY_STRING', ''):
        param = urlparse.parse_qs(request.META.get('QUERY_STRING'))
        values = param.get('host')
        if values:
            host = next(iter(values), None)
    return host


class LaunchInstanceLink(tables.LinkAction):
    name = "launch"
    url = "horizon:dbaas_ui:shortcuts:launch_instance"
    verbose_name = _("Launch Instance")
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"


class RestartInstanceLink(tables.LinkAction):
    name = "restartInstance"
    verbose_name = _("Restart")
    url = "horizon:dbaas_ui:shortcuts:restart_instance"
    classes = ("ajax-modal",)
    icon = "refresh"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE' or
                instance.status == 'SHUTDOWN' or
                instance.status == 'RESTART_REQUIRED')


class ResizeInstanceLink(tables.LinkAction):
    name = "resizeInstance"
    verbose_name = _("Resize Instance")
    url = "horizon:dbaas_ui:shortcuts:resize_instance"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE' or
                instance.status == 'SHUTOFF')


class RenameInstanceLink(tables.LinkAction):
    name = "renameInstance"
    verbose_name = _("Rename Instance")
    url = "horizon:dbaas_ui:shortcuts:rename_instance"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"


class ResizeVolumeLink(tables.LinkAction):
    name = "resizeVolume"
    verbose_name = _("Resize Volume")
    url = "horizon:dbaas_ui:shortcuts:resize_volume"
    classes = ("ajax-modal",)
    icon = "sort-amount-desc"

    def allowed(self, request, instance=None):
        return (instance.status == 'ACTIVE')


"""
class UpgradeInstanceLink(tables.LinkAction):
    name = "upgradeInstance"
    verbose_name = _("Upgrade Instance")
    url = "horizon:dbaas_ui:shortcuts:upgrade_instance"
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
    url = "horizon:dbaas_ui:shortcuts:delete_instance"
    classes = ("ajax-modal", "btn-danger")
    icon = "trash"


class CreateUserLink(tables.LinkAction):
    name = "create_user"
    verbose_name = _("Create User")
    url = "horizon:dbaas_ui:shortcuts:create_user"
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
    url = "horizon:dbaas_ui:shortcuts:create_backup"
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
    url = "horizon:dbaas_ui:shortcuts:create_database"
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


class DeleteBackupLink(tables.LinkAction):
    # Always allowed in table of backups
    name = "deleteBackup"
    verbose_name = _("Delete")
    url = "horizon:dbaas_ui:shortcuts:delete_backup"
    classes = ("ajax-modal", "btn-danger")
    icon = "trash"


class DeleteUserLink(tables.LinkAction):
    # Always allowed in table of users
    name = "deleteUser"
    verbose_name = _("Delete")
    url = "horizon:dbaas_ui:shortcuts:delete_user"
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
    url = "horizon:dbaas_ui:shortcuts:delete_database"
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
    url = "horizon:dbaas_ui:shortcuts:restore_from_backup"
    classes = ("ajax-modal",)
    icon = "cloud-upload"

    def allowed(self, request, backup=None):
        return backup.status == 'COMPLETED'

    def get_link_url(self, datum):
        url = reverse(self.url)
        return url + '?backup=%s' % datum.id


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
    url = "horizon:dbaas_ui:shortcuts:manage_user"
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
    url = "horizon:dbaas_ui:shortcuts:manage_root"

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
