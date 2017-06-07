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

from django import template
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

import logging

from dbaas_ui.instances import tables
from dbaas_ui.shortcuts import tasks

from trove_dashboard import api as trove_api
from trove_dashboard.content.databases import db_capability


class InstanceOverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "instance_overview"
    template_name = ("dbaas_ui/instances/_instance_detail_overview.html")

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
        template_file = ('dbaas_ui/instances/_detail_overview_%s.html' %
                         self._get_template_type(instance.datastore['type']))
        try:
            template.loader.get_template(template_file)
            return template_file
        except template.TemplateDoesNotExist:
            # This datastore type does not have a template file
            # Just use the base template file
            return ('dbaas_ui/instances/_detail_overview.html')

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
        return tasks.has_user_add_perm(request)


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
        return tasks.has_database_add_perm(request)


class InstanceDetailsTabs(tabs.TabGroup):
    slug = "instance_details"
    tabs = (InstanceOverviewTab, UserTab, DatabaseTab, InstanceBackupsTab)
