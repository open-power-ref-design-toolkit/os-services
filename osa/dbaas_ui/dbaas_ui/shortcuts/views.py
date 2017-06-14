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
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tabs as baseTabs
from horizon import tables as baseTables
from horizon.utils import memoized
from horizon import workflows as horizon_workflows

import logging

from dbaas_ui.shortcuts import tabs as database_tabs
from dbaas_ui.shortcuts import forms as project_forms
from dbaas_ui.shortcuts import tables as project_tables
from dbaas_ui.shortcuts import workflows as aggregate_workflows

from trove_dashboard import api as trove_api


def go_to_instances():
    return reverse_lazy('horizon:dbaas_ui:instances:index')


def go_to_backups():
    return reverse_lazy('horizon:dbaas_ui:backups:index')


def build_instance_details_url(instance_id, target_tab=None):
    if target_tab:
        return reverse('horizon:dbaas_ui:instances:detail',
                       args=(instance_id,)) + target_tab
    else:
        return reverse('horizon:dbaas_ui:instances:detail',
                       args=(instance_id,))


# View that displays the shortcuts panel
class IndexView(baseTabs.TabView):
    tab_group_class = database_tabs.DatabasePageTabs
    template_name = 'dbaas_ui/shortcuts/index.html'
    page_title = _("Shortcuts")


# Views for all actions that shortcuts, instances and backups call
class LaunchInstanceView(horizon_workflows.WorkflowView):
    workflow_class = aggregate_workflows.LaunchInstance
    form_id = "launch_instance_form"
    submit_label = _("Launch")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:launch_instance")
    success_url = go_to_instances()

    def get_initial(self):
        initial = super(LaunchInstanceView, self).get_initial()
        initial['project_id'] = self.request.user.project_id
        initial['user_id'] = self.request.user.id

        return initial


class RestoreFromBackupView(LaunchInstanceView):
    workflow_class = aggregate_workflows.RestoreFromBackup
    submit_label = _("Restore")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:restore_from_backup")


class CreateBackupView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/create_backup.html'
    modal_header = _("Create Backup")
    form_id = "create_backup_form"
    form_class = project_forms.CreateBackupForm
    submit_label = _("Create")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:create_backup")
    success_url = go_to_backups()
    page_title = _("Create Backup")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class RestartInstanceView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/restart_instance.html'
    modal_header = _("Restart Instance")
    modal_id = "restart_instance_modal"
    form_id = "restart_instance_form"
    form_class = project_forms.RestartInstanceForm
    submit_label = _("Restart")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:restart_instance")
    success_url = go_to_instances()
    page_title = _("Restart Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class ResizeInstanceView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/resize_instance.html'
    modal_header = _("Resize Instance")
    form_id = "resize_instance_form"
    form_class = project_forms.ResizeInstanceForm
    submit_label = _("Resize")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:resize_instance")
    success_url = go_to_instances()
    page_title = _("Resize Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class ResizeVolumeView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/resize_volume.html'
    modal_header = _("Resize Volume")
    form_id = "resize_volume_form"
    form_class = project_forms.ResizeVolumeForm
    submit_label = _("Resize")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:resize_volume")
    success_url = go_to_instances()
    page_title = _("Resize Volume")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class RenameInstanceView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/rename_instance.html'
    modal_header = _("Rename Instance")
    form_id = "rename_instance_form"
    form_class = project_forms.RenameInstanceForm
    submit_label = _("Rename")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:rename_instance")
    success_url = go_to_instances()
    page_title = _("Rename Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class UpgradeInstanceView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/upgrade_instance.html'
    modal_header = _("Upgrade Instance")
    form_id = "upgrade_instance_form"
    form_class = project_forms.UpgradeInstanceForm
    submit_label = _("Upgrade")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:upgrade_instance")
    success_url = go_to_instances()
    page_title = _("Upgrade Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class DeleteInstanceView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/delete_instance.html'
    modal_header = _("Delete Instance")
    form_id = "delete_instance_form"
    form_class = project_forms.DeleteInstanceForm
    submit_label = _("Delete")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:delete_instance")
    success_url = go_to_instances()
    page_title = _("Delete Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return


class DeleteBackupView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/delete_backup.html'
    modal_header = _("Delete Backup")
    form_id = "delete_backup_form"
    form_class = project_forms.DeleteBackupForm
    submit_label = _("Delete")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:delete_backup")
    success_url = go_to_backups()
    page_title = _("Delete Backup")

    def get_initial(self):
        # Need the backup id to prime the dialog if passed in
        if "backup_id" in self.kwargs:
            return {'backup_id': self.kwargs['backup_id']}
        else:
            return


class CreateUserView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/create_user.html'
    modal_header = _("Create User")
    form_id = "create_user_form"
    form_class = project_forms.CreateUserForm
    submit_label = _("Create")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:create_user")
    success_url = go_to_instances()
    page_title = _("Create User")
    instance_id = None

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            self.instance_id = self.kwargs['instance_id']
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # Try to retrieve the selected_instance (id) from the session
        if hasattr(self.request, 'session'):
            if 'instance_id' in self.request.session:
                return build_instance_details_url(
                    self.request.session['instance_id'],
                    '?tab=instance_details__users_tab')

        # We were not able to retrieve the instance_id that the
        # user was created on.  Just redirect to to the list
        # of instances.
        return go_to_instances()


class DeleteUserView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/delete_user.html'
    modal_header = _("Delete User")
    form_id = "delete_user_form"
    form_class = project_forms.DeleteUserForm
    submit_label = _("Delete")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:delete_user")
    success_url = go_to_instances()
    page_title = _("Delete User")

    def get_initial(self):
        # Need the instance and user to prime the dialog if passed in
        if "user_id" in self.kwargs:
            return {'user_id': self.kwargs['user_id']}
        else:
            return

    def get_context_data(self, **kwargs):
        context = super(DeleteUserView, self).get_context_data(**kwargs)
        context["instance_id"] = kwargs.get("instance_id")
        self._instance = context['instance_id']
        return context

    def get_success_url(self):
        # Try to retrieve the selected_instance (id) from the session
        if hasattr(self.request, 'session'):
            if 'instance_id' in self.request.session:
                return build_instance_details_url(
                    self.request.session['instance_id'],
                    '?tab=instance_details__users_tab')

        # We were not able to retrieve the instance_id that the
        # user was deleted from on.  Just redirect to to the list
        # of instances.
        return go_to_instances()


class CreateDatabaseView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/create_database.html'
    modal_header = _("Create Database")
    form_id = "create_database_form"
    form_class = project_forms.CreateDatabaseForm
    submit_label = _("Create")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:create_database")
    success_url = go_to_instances()
    page_title = _("Create Database")
    instance_id = None

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            self.instance_id = self.kwargs['instance_id']
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # Try to retrieve the selected_instance (id) from the session
        if hasattr(self.request, 'session'):
            if 'instance_id' in self.request.session:
                return build_instance_details_url(
                    self.request.session['instance_id'],
                    '?tab=instance_details__database_tab')

        # We were not able to retrieve the instance_id that the
        # database was created on.  Just redirect to to the list
        # of instances.
        return go_to_instances()


class DeleteDatabaseView(forms.ModalFormView):
    template_name = 'dbaas_ui/shortcuts/delete_database.html'
    modal_header = _("Delete Database")
    form_id = "delete_database_form"
    form_class = project_forms.DeleteDatabaseForm
    submit_label = _("Delete")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:delete_database")
    success_url = go_to_instances()
    page_title = _("Delete Database")

    def get_initial(self):
        # Need the database to prime the dialog if passed in
        if "database_id" in self.kwargs:
            return {'database_id': self.kwargs['database_id']}
        else:
            return

    def get_context_data(self, **kwargs):
        context = super(DeleteDatabaseView, self).get_context_data(**kwargs)
        context["instance_id"] = kwargs.get("instance_id")
        self._instance = context['instance_id']
        return context

    def get_success_url(self):
        # Try to retrieve the selected_instance (id) from the session
        if hasattr(self.request, 'session'):
            if 'instance_id' in self.request.session:
                return build_instance_details_url(
                    self.request.session['instance_id'],
                    '?tab=instance_details__database_tab')

        # We were not able to retrieve the instance_id that the
        # user was created on.  Just redirect to to the list
        # of instances.
        return go_to_instances()


class EnableRootInfo(object):
    # This class holds enablement information for the root profile for
    # an instance.  This is used to build the manage root access dialog
    def __init__(self, instance_id, instance_name, enabled, password=None):
        self.id = instance_id
        self.name = instance_name
        self.enabled = enabled
        self.password = password


class DBAccess(object):
    # this class holds the access the user has for a database
    # (database name, database access)
    def __init__(self, name, access):
        self.name = name
        self.access = access


class ManageRootView(baseTables.DataTableView):
    # The purpose of this view is to open a dialog showing the enablement of
    # of the superuser profile (root) on the selected instance.  The user can
    # enable and disable the profile, and reset the password.
    table_class = project_tables.ManageRootTable
    template_name = 'dbaas_ui/shortcuts/manage_root.html'
    page_title = _("Manage Root Access")

    @memoized.memoized_method
    def get_data(self):
        # Retrieve the instance (based on instance id) -- required
        # to display the instance ID
        instance_id = self.kwargs['instance_id']
        try:
            instance = trove_api.trove.instance_get(self.request, instance_id)
        except Exception:
            redirect = build_instance_details_url(
                instance_id,)

            exceptions.handle(self.request,
                              _('Unable to retrieve instance details.'),
                              redirect=redirect)

        # Identify if root has ever been enabled (based on instance id)
        try:
            enabled = trove_api.trove.root_show(self.request, instance_id)
        except Exception:
            redirect = build_instance_details_url(
                instance_id,)
            exceptions.handle(self.request,
                              _('Unable to determine if root is enabled '
                                'on the selected instance.'),
                              redirect=redirect)

        # Build a 'root enabled' object to get added to the table
        root_enabled_list = []
        root_enabled_info = EnableRootInfo(instance.id,
                                           instance.name,
                                           enabled.rootEnabled)
        root_enabled_list.append(root_enabled_info)

        return root_enabled_list

    def get_context_data(self, **kwargs):
        context = super(ManageRootView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context


class ManageUserView(baseTables.DataTableView):
    table_class = project_tables.ManageUserDBTable
    template_name = 'dbaas_ui/shortcuts/manage_user.html'
    # We don't have the instance name on which the user is
    # being managed. Set the title based on the user passed
    # in, and we'll try to override it later.
    page_title = _("Database Access for: {{ user_name }}")

    @memoized.memoized_method
    def get_data(self):
        __method__ = "views.ManageUserView.get_data"
        instance_id = self.kwargs['instance_id']
        user_name = self.kwargs['user_name']
        instance = None

        # Retrieve the instance (so we can update the page title)
        try:
            instance = trove_api.trove.instance_get(self.request, instance_id)
            # Now that we have the instance, override the title
            self.page_title = ("Database Access for: %(user_name)s on "
                               "%(instance_name)s" % {'user_name':
                                                      user_name,
                                                      'instance_name':
                                                      instance.name})
        except Exception as e:
            # log the error, but don't externalize it.  Just proceed with the
            # page title as it is.
            logging.error("%s: Exception trying to retrieve the selected "
                          "instance %s.  The exception "
                          " is: %s", __method__, instance_id, e)

        # Retrieve the databases defined on the instance
        try:
            databases = trove_api.trove.database_list(self.request,
                                                      instance_id)
        except Exception as e:
            # Without the databases, we can't continue with this function
            logging.error("Exception trying to retrieve the list of databases"
                          " for instance %s.  The exception "
                          " is: %s", __method__, instance_id, e)

            databases = []
            # Redirect to the users tab for the instance
            redirect = build_instance_details_url(
                instance_id, '?tab=instance_details__users_tab')

            exceptions.handle(self.request,
                              _('Unable to retrieve databases.'),
                              redirect=redirect)

        # Retrieve the databases the user has access to
        try:
            granted = trove_api.trove.user_list_access(
                self.request, instance_id, user_name)
        except Exception:
            # Without the list of databases the user has access to,
            # we can't continue with this function
            logging.error("Exception trying to retrieve the list of databases"
                          " the user has access to on instance %s.  The"
                          " exception is: %s", __method__, instance_id, e)

            granted = []
            # Redirect to the users tab for the instance
            redirect = build_instance_details_url(
                instance_id, '?tab=instance_details__users_tab')

            exceptions.handle(self.request,
                              _('Unable to retrieve accessible databases.'),
                              redirect=redirect)

        db_access_list = []
        for database in databases:
            if database in granted:
                access = True
            else:
                access = False

            db_access = DBAccess(database.name, access)
            db_access_list.append(db_access)

        return sorted(db_access_list, key=lambda data: (data.name))

    def get_context_data(self, **kwargs):
        context = super(ManageUserView, self).get_context_data(**kwargs)
        context["db_access"] = self.get_data()
        return context


class ManageRootNoContextView(forms.ModalFormView):
    # The purpose of this view is to prompt the user for the context
    # on which manage root access should be done
    template_name = 'dbaas_ui/shortcuts/manage_root_no_context.html'
    modal_header = _("Manage Root Access")
    form_id = "manage_root_no_context_form"
    form_class = project_forms.ManageRootNoContextForm
    submit_label = _("Manage Root Access")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:manage_root")
    success_url = go_to_instances()
    page_title = _("Manage Root Access")

    def get_success_url(self):
        # Try to retrieve the selected_instance (id) from the session
        if hasattr(self.request, 'session'):
            if 'instance_id' in self.request.session:
                instance_id = self.request.session['instance_id']
                # redirect to the manage root access link....
                return reverse('horizon:dbaas_ui:shortcuts:manage_root',
                               args=(instance_id,))

        # We did not have the required information to allow user to
        # manage root access.
        msg = _('A problem occurred trying to launch Manage Root Access.')
        messages.error(self.request, msg)

        logging.error("%s: Unable to launch into manage root function "
                      "because the selected instance ID was not found "
                      "on the session.")

        # We were not able to retrieve the instance_id the
        # user just selected.  Display the message, and redirect the user
        # to the list of instances.
        return go_to_instances()


class ManageUserNoContextView(forms.ModalFormView):
    # The purpose of this view is to prompt the user for the context
    # on which manage user access should be done
    template_name = 'dbaas_ui/shortcuts/manage_user_no_context.html'
    modal_header = _("Manage User Access")
    form_id = "manage_user_no_context_form"
    form_class = project_forms.ManageUserNoContextForm
    submit_label = _("Manage User Access")
    submit_url = reverse_lazy("horizon:dbaas_ui:shortcuts:manage_user")
    success_url = go_to_instances()
    page_title = _("Manage User Access")

    def get_success_url(self):
        # Try to retrieve the selected user and instance (id) from the session
        if hasattr(self.request, 'session'):
            if ('instance_id' in self.request.session and
                    'user' in self.request.session):
                instance_id = self.request.session['instance_id']
                user = self.request.session['user']
                # redirect to the manage root access link....
                return reverse('horizon:dbaas_ui:shortcuts:manage_user',
                               args=(instance_id, user))

        # We did not have the required information to allow user to
        # manage user access
        msg = _('A problem occurred trying to launch Manage User Access.')
        messages.error(self.request, msg)

        logging.error("%s: Unable to launch into manage user function "
                      "because the selected instance ID was not found "
                      "on the session.")

        # We were not able to retrieve the instance_id the
        # user just selected.  Display the message, and redirect the user
        # to the list of instances.
        return go_to_instances()
