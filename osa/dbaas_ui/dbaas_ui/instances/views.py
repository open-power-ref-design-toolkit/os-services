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
import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

import six

from horizon import exceptions, messages
from horizon import tabs as baseTabs
from horizon import tables as baseTables
from horizon.utils import memoized

from trove_dashboard import api as trove_api

from dbaas_ui.instances import tables, tabs


class IndexView(baseTables.DataTableView):
    table_class = tables.InstancesTable
    template_name = 'dbaas_ui/instances/index.html'
    page_title = _("Instances")

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
        instance.host = tables.get_host(instance)
        return instance

    def get_data(self):
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


class InstanceDetailsView(baseTabs.TabView):
    tab_group_class = tabs.InstanceDetailsTabs
    template_name = 'horizon/common/_detail.html'
    # Ensure the title indicates what type of item being viewed (instance)
    page_title = "Instance: {{ instance.name }}"

    def get_context_data(self, **kwargs):
        context = super(InstanceDetailsView, self).get_context_data(**kwargs)
        instance = self.get_data()
        table = tables.InstancesTable(self.request)
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
            instance.host = tables.get_host(instance)
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
        return reverse('horizon:dbaas_ui:instances:index')
