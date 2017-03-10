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

from horizon import forms
from horizon import tabs as baseTabs
from horizon import workflows as horizon_workflows

from dbaas_ui import forms as project_forms
from dbaas_ui import tabs as database_tabs
from dbaas_ui import workflows as aggregate_workflows


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
        # On completion, ensure we navigate to the instances tab
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
        # On completion, ensure we navigate to the backups tab
        return build_url_tab('?tab=database_page__backups')


class RestartInstanceView(forms.ModalFormView):
    template_name = 'project/database/restart_instance.html'
    modal_header = _("Restart Instance")
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
        # On completion, ensure we navigate to the instances tab
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
        # On completion, ensure we navigate to the instances tab
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
        # On completion, ensure we navigate to the instances tab
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
        # On completion, ensure we navigate to the instances tab
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
        # On completion, ensure we navigate to the backups tab
        return build_url_tab('?tab=database_page__backups')
