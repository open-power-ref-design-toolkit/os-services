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
from horizon import views as horizon_views
from horizon import workflows as horizon_workflows
from horizon.utils import filters
from horizon.utils import memoized

import logging

from dbaas_ui import forms as project_forms
from dbaas_ui import tabs as database_tabs
from dbaas_ui import tables as project_tables
from dbaas_ui import workflows as aggregate_workflows

from trove_dashboard import api as trove_api


def build_url_tab(target_tab):
    return reverse('horizon:project:database:index') + target_tab


class IndexView(baseTabs.TabView):
    tab_group_class = database_tabs.DatabasePageTabs
    template_name = 'project/database/index.html'
    page_title = _("Database as a Service")


class LaunchInstanceView(horizon_workflows.WorkflowView):
    workflow_class = aggregate_workflows.LaunchInstance
    form_id = "launch_instance_form"
    submit_label = _("Launch")
    submit_url = reverse_lazy("horizon:project:database:launch_instance")
    success_url = reverse_lazy('horizon:project:database:index')

    def get_success_url(self):
        # On successful completion, navigate to the instances tab
        return build_url_tab('?tab=database_page__instances')

    def get_initial(self):
        initial = super(LaunchInstanceView, self).get_initial()
        initial['project_id'] = self.request.user.project_id
        initial['user_id'] = self.request.user.id

        return initial


class RestoreFromBackupView(LaunchInstanceView):
    workflow_class = aggregate_workflows.RestoreFromBackup
    submit_label = _("Restore")
    submit_url = reverse_lazy("horizon:project:database:restore_backup")


class CreateBackupView(forms.ModalFormView):
    template_name = 'project/database/create_backup.html'
    modal_header = _("Create Backup")
    form_id = "create_backup_form"
    form_class = project_forms.CreateBackupForm
    submit_label = _("Create")
    submit_url = reverse_lazy("horizon:project:database:create_backup")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Create Backup")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, navigate to the backups tab
        return build_url_tab('?tab=database_page__backups')


class RestartInstanceView(forms.ModalFormView):
    template_name = 'project/database/restart_instance.html'
    modal_header = _("Restart Instance")
    modal_id = "restart_instance_modal"
    form_id = "restart_instance_form"
    form_class = project_forms.RestartInstanceForm
    submit_label = _("Restart")
    submit_url = reverse_lazy("horizon:project:database:restart_instance")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Restart Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, navigate to the instances tab
        return build_url_tab('?tab=database_page__instances')


class ResizeInstanceView(forms.ModalFormView):
    template_name = 'project/database/resize_instance.html'
    modal_header = _("Resize Instance")
    form_id = "resize_instance_form"
    form_class = project_forms.ResizeInstanceForm
    submit_label = _("Resize")
    submit_url = reverse_lazy("horizon:project:database:resize_instance")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Resize Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, navigate to the instances tab
        return build_url_tab('?tab=database_page__instances')


class ResizeVolumeView(forms.ModalFormView):
    template_name = 'project/database/resize_volume.html'
    modal_header = _("Resize Volume")
    form_id = "resize_volume_form"
    form_class = project_forms.ResizeVolumeForm
    submit_label = _("Resize")
    submit_url = reverse_lazy("horizon:project:database:resize_volume")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Resize Volume")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, navigate to the instances tab
        return build_url_tab('?tab=database_page__instances')


class RenameInstanceView(forms.ModalFormView):
    template_name = 'project/database/rename_instance.html'
    modal_header = _("Rename Instance")
    form_id = "rename_instance_form"
    form_class = project_forms.RenameInstanceForm
    submit_label = _("Rename")
    submit_url = reverse_lazy("horizon:project:database:rename_instance")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Rename Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, navigate to the instances tab
        return build_url_tab('?tab=database_page__instances')


class DeleteInstanceView(forms.ModalFormView):
    template_name = 'project/database/delete_instance.html'
    modal_header = _("Delete Instance")
    form_id = "delete_instance_form"
    form_class = project_forms.DeleteInstanceForm
    submit_label = _("Delete")
    submit_url = reverse_lazy("horizon:project:database:delete_instance")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Delete Instance")

    def get_initial(self):
        # Need the instance id to prime the dialog if passed in
        if "instance_id" in self.kwargs:
            return {'instance_id': self.kwargs['instance_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, navigate to the instances tab
        return build_url_tab('?tab=database_page__instances')


class DeleteBackupView(forms.ModalFormView):
    template_name = 'project/database/delete_backup.html'
    modal_header = _("Delete Backup")
    form_id = "delete_backup_form"
    form_class = project_forms.DeleteBackupForm
    submit_label = _("Delete")
    submit_url = reverse_lazy("horizon:project:database:delete_backup")
    success_url = reverse_lazy('horizon:project:database:index')
    page_title = _("Delete Backup")

    def get_initial(self):
        # Need the backup id to prime the dialog if passed in
        if "backup_id" in self.kwargs:
            return {'backup_id': self.kwargs['backup_id']}
        else:
            return

    def get_success_url(self):
        # On successful completion, we navigate to the backups tab
        return build_url_tab('?tab=database_page__backups')


class InstanceDetailsView(baseTabs.TabView):
    tab_group_class = database_tabs.InstanceDetailsTabs
    template_name = 'horizon/common/_detail.html'
    # Ensure the title indicates what type of item being viewed (instance)
    page_title = "Instance: {{ instance.name }}"

    def get_context_data(self, **kwargs):
        context = super(InstanceDetailsView, self).get_context_data(**kwargs)
        instance = self.get_data()
        table = project_tables.InstancesTable(self.request)
        context["instance"] = instance
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(instance)
        return context

    @memoized.memoized_method
    def get_data(self):
        # Returns the selected instance (based on the instance id)
        __method__ = "views.InstanceDetailsView.get_data"
        failure_message = "Unable to retrieve instance details."
        try:
            # Retrieve the instance id passed in and use it to
            # get the instance.
            instance_id = self.kwargs['instance_id']
            instance = trove_api.trove.instance_get(self.request, instance_id)
            instance.host = project_tables.get_host(instance)
        except Exception as e:
            logging.error("%s: Exception received trying to retrieve"
                          " instance information.  Exception is: %s",
                          __method__, e)
            # Redirect so that incomplete (or non-existant) instance
            # information is not displayed
            exceptions.handle(self.request, failure_message,
                              redirect=self.get_redirect_url())
        try:
            # Flavor information needs to be retrieved for the instance
            instance.full_flavor = trove_api.trove.flavor_get(
                self.request, instance.flavor["id"])
        except Exception as e:
            logging.error('%s: Exception received trying to retrieve flavor '
                          'details for database instance: %s.  Exception '
                          'is: %s', __method__, instance_id, e)

            # Issue warning that flavor information couldn't be retrieved, but
            # go ahead and allow the details to be displayed.
            msg = _('Instance size information (flavor) could not'
                    ' be retrieved.')
            messages.warning(self.request, msg)

        return instance

    def get_tabs(self, request, *args, **kwargs):
        return self.tab_group_class(request,
                                    instance=self.get_data(),
                                    **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:project:database:index')


class BackupDetailsView(horizon_views.APIView):
    template_name = "project/database/_backup_detail_overview.html"
    # Ensure the title indicates the type of item being viewed (instance)
    page_title = _("Backup Details: {{ backup.name }}")

    def get_data(self, request, context, *args, **kwargs):
        __method__ = "views.InstanceDetailsView.get_data"
        failure_message = "Unable to retrieve backup details."

        backup_id = kwargs.get("backup_id")
        try:
            # Use the backup id passed in to retrieve the backup
            backup = trove_api.trove.backup_get(request, backup_id)
            created_at = filters.parse_isotime(backup.created)
            updated_at = filters.parse_isotime(backup.updated)
            backup.duration = updated_at - created_at
        except Exception:
            # Redirect so that incomplete (or non-existant) backup
            # information is not displayed
            exceptions.handle(self.request, failure_message,
                              redirect=self.get_redirect_url())

        try:
            # Try to retrieve parent information (if present)
            if(hasattr(backup, 'parent_id') and backup.parent_id is not None):
                backup.parent = trove_api.trove.backup_get(request,
                                                           backup.parent_id)
        except Exception as e:
            # This is a problem -- the information indicates a parent exists,
            # but the parent could not be retrieved...There is a gap in the
            # incremental backup
            logging.error('%s: Exception received trying to retrieve parent '
                          'details for database backup: %s.  Exception '
                          'is: %s', __method__, backup_id, e)

            backup.parent = None

            msg = _('A problem occurred trying to retrieve parent information '
                    'for the incremental backup.  Parent information could '
                    'not be displayed.')
            messages.error(self.request, msg)

        try:
            # try to retrieve instance information (if present) -- the backup
            # may have been created for an instance that no longer exists --
            # this is not a failure case --  no warning/error needed
            instance = trove_api.trove.instance_get(request,
                                                    backup.instance_id)
        except Exception as e:
            instance = None
        context['backup'] = backup
        context['instance'] = instance
        return context

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:project:database:index')
