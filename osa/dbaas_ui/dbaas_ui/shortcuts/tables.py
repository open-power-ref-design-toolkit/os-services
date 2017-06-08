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
from django.template import defaultfilters as d_filters

from django.utils.translation import ugettext_lazy as _

from dbaas_ui.shortcuts import tasks

from horizon import tables


class ManageUserDBTable(tables.DataTable):
    dbname = tables.Column("name", verbose_name=_("Database Name"))
    access = tables.Column(
        "access",
        verbose_name=_("Accessible"),
        filters=(d_filters.yesno, d_filters.capfirst))

    class Meta(object):
        name = "access"
        verbose_name = _("Database Access")
        row_actions = (tasks.GrantDBAccess, tasks.RevokeDBAccess)

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
        row_actions = (tasks.EnableRootAction, tasks.DisableRootAction,)
