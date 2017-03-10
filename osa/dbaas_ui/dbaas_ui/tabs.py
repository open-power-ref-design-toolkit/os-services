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
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon.utils import memoized
from horizon import tabs

import six

import tables as tables
from trove_dashboard import api as trove_api


@memoized.memoized_method
def get_flavors(request):
    try:
        flavors = trove_api.trove.flavor_list(request)
    except Exception:
        flavors = []
        msg = _('Unable to retrieve database size information.')
        exceptions.handle(request, msg)
    return OrderedDict((six.text_type(flavor.id), flavor)
                       for flavor in flavors)


def get_host(instance):
    if hasattr(instance, "hostname"):
        return instance.hostname
    elif hasattr(instance, "ip") and instance.ip:
        return instance.ip[0]
    return _("Not Assigned")


class ShortcutsTab(tabs.Tab):
    # The Shortcuts tab does not directly display database data.  Instead,
    # it contains tasks and task groups.
    name = _("Shortcuts")
    slug = "shortcuts"
    template_name = "project/database/_shortcuts_tab.html"


class InstancesTab(tabs.TableTab):
    name = _("Instances")
    slug = "instances"
    table_classes = (tables.InstancesTable,)
    template_name = "project/database/_instances_tab.html"

    def has_more_data(self, table):
        return self._more

    @memoized.memoized_method
    def get_flavors(self):
        try:
            flavors = trove_api.trove.flavor_list(self.request)
        except Exception:
            flavors = []
            msg = _('Unable to retrieve database size information.')
            exceptions.handle(self.request, msg)
        return OrderedDict((six.text_type(flavor.id), flavor)
                           for flavor in flavors)

    def _extra_data(self, instance):
        flavor = self.get_flavors().get(instance.flavor["id"])
        if flavor is not None:
            instance.full_flavor = flavor
        instance.host = get_host(instance)
        return instance

    def get_instances_data(self):
        marker = self.request.GET.get(
            tables.InstancesTable._meta.pagination_param)
        # Gather our instances
        try:
            instances = trove_api.trove.instance_list(self.request,
                                                      marker=marker)
            self._more = instances.next or False
        except Exception:
            self._more = False
            instances = []
            msg = _('Unable to retrieve database instances.')
            exceptions.handle(self.request, msg)
        map(self._extra_data, instances)
        return instances


class BackupsTab(tabs.TableTab):
    name = _("Backups")
    slug = "backups"
    table_classes = (tables.BackupsTable,)
    template_name = "project/database/_backups_tab.html"

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

    def get_backups_data(self):
        # retrieve database datastores
        backups = []
        try:
            backups = trove_api.trove.backup_list(self.request)
            backups = map(self._get_extra_data, backups)
        except Exception:
            msg = _('Unable to retrieve list of backups.')
            exceptions.handle(self.request, msg)
        return backups


class DatabasePageTabs(tabs.TabGroup):
    slug = "database_page"
    # Database page has a welcome/main tab and several sub-tabs
    tabs = (ShortcutsTab, InstancesTab, BackupsTab,)
    show_single_tab = True
