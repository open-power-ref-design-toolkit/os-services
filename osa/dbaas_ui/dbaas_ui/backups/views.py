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
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import messages
from horizon.utils import filters
from horizon import tables as baseTables
from horizon import views as horizon_views

import logging

from dbaas_ui.backups import tables

from trove_dashboard import api as trove_api


class IndexView(baseTables.DataTableView):
    table_class = tables.BackupsTable
    template_name = 'dbaas_ui/backups/index.html'
    page_title = _("Backups")

    def _get_extra_data(self, backup):
        """Apply extra info to the backup."""
        inst_id = backup.instance_id
        if not hasattr(self, '_instances'):
            self._instances = {}
        instance = self._instances.get(inst_id)
        if instance is None:
            try:
                instance = trove_api.trove.instance_get(self.request, inst_id)
            except Exception:
                instance = _('Not Found')
        backup.instance = instance
        return backup

    def get_data(self):
        # retrieve database datastores
        backups = []
        try:
            backups = trove_api.trove.backup_list(self.request)
            backups = map(self._get_extra_data, backups)
        except Exception:
            msg = _('Unable to retrieve list of backups.')
            exceptions.handle(self.request, msg)
        return backups


class BackupDetailsView(horizon_views.APIView):
    template_name = "dbaas_ui/backups/_backup_detail_overview.html"
    # Ensure the title indicates the type of item being viewed (instance)
    page_title = _("Backup Details: {{ backup.name }}")

    def get_data(self, request, context, *args, **kwargs):
        __method__ = "views.BackupDetailsView.get_data"
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
        return reverse('horizon:dbaas_ui:backups:index')
