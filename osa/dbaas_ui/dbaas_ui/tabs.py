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

from django import template
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs
from horizon.utils import memoized

import logging
import six

import tables as tables
from trove_dashboard import api as trove_api
from trove_dashboard.content.databases import db_capability


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
    template_name = "horizon/common/_detail_table.html"
    preload = False

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
    template_name = "horizon/common/_detail_table.html"
    preload = False

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
    sticky = True


class InstanceOverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "instance_overview"
    template_name = ("project/database/_instance_detail_overview.html")

    def get_context_data(self, request):
        __method__ = "tabs.InstanceOverviewTab.get_context_data"
        # Place the instance passed in onto the context
        instance = self.tab_group.kwargs['instance']
        context = {"instance": instance}
        try:
            # Indicate if root is enabled and place that on the context
            root_show = trove_api.trove.root_show(request, instance.id)
            context["root_enabled"] = template.defaultfilters.yesno(
                root_show.rootEnabled)
        except Exception as e:
            logging.error("%s:  Exception received trying to "
                          "retrieve root_show: %s", __method__, e)
            context["root_enabled"] = _('Unable to obtain information on '
                                        'root user')
        return context

    def get_template_name(self, request):
        # in addition to _instance_detail_overview.html as the
        # template for instance details, there are additional
        # template portions based on the datastore type of the
        # instance
        instance = self.tab_group.kwargs['instance']
        template_file = ('project/database/_detail_overview_%s.html' %
                         self._get_template_type(instance.datastore['type']))
        try:
            template.loader.get_template(template_file)
            return template_file
        except template.TemplateDoesNotExist:
            # This datastore type does not have a template file
            # Just use the base template file
            return ('project/databases/_detail_overview.html')

    def _get_template_type(self, datastore):
        if db_capability.is_mysql_compatible(datastore):
            return 'mysql'

        return datastore


class UserTab(tabs.TableTab):
    table_classes = [tables.UsersTable]
    name = _("Users")
    slug = "users_tab"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_users_data(self):
        __method__ = "tabs.UserTab.get_users_data"
        instance = self.tab_group.kwargs['instance']
        try:
            # Retrieve all users for the selected instance
            data = trove_api.trove.users_list(self.request, instance.id)

            for user in data:
                user.instance = instance
                try:
                    # Set the user's access to the instance
                    user.access = trove_api.trove.user_list_access(
                        self.request,
                        instance.id,
                        user.name)
                except exceptions.NOT_FOUND:
                    pass
                except Exception as e:
                    logging.error("%s: Exception received trying to retrieve "
                                  " user information for instance %s.  "
                                  "Exception : %s",
                                  __method__, instance.name, e)
                    msg = _('Unable to retrieve user data for the selected '
                            'instance.')
                    exceptions.handle(self.request, msg)
        except Exception as e:
            logging.error("%s: Exception received trying to retrieve user "
                          "information for instance %s.  "
                          "Exception : %s", __method__, instance.name, e)
            msg = _('Unable to retrieve user data for selected instance.')
            exceptions.handle(self.request, msg)
            data = []
        return data

    def allowed(self, request):
        return tables.has_user_add_perm(request)


class InstanceBackupsTab(tabs.TableTab):
    table_classes = [tables.InstanceBackupsTable]
    name = _("Backups")
    slug = "instance_backups_tab"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_backups_data(self):
        instance = self.tab_group.kwargs['instance']

        # retrieve backups for the selected instance
        backups = []
        try:
            backups = trove_api.trove.instance_backups(self.request,
                                                       instance.id)
        except Exception:
            msg = _('Unable to retrieve list of backups for '
                    'instance: %s.', instance.name)
            exceptions.handle(self.request, msg)
        return backups


class DatabaseTab(tabs.TableTab):
    table_classes = [tables.DatabaseTable]
    name = _("Databases")
    slug = "database_tab"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_databases_data(self):
        instance = self.tab_group.kwargs['instance']
        try:
            data = trove_api.trove.database_list(self.request, instance.id)
            for db in data:
                setattr(db, 'instance', instance)
        except Exception:
            msg = _('Unable to get databases data.')
            exceptions.handle(self.request, msg)
            data = []
        return data

    def allowed(self, request):
        return tables.has_database_add_perm(request)


class InstanceDetailsTabs(tabs.TabGroup):
    slug = "instance_details"
    tabs = (InstanceOverviewTab, UserTab, DatabaseTab, InstanceBackupsTab)
