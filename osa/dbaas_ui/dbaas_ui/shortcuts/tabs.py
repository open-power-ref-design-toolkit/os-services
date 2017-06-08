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

from django.utils.translation import ugettext_lazy as _

from horizon import tabs


class ShortcutsTab(tabs.Tab):
    # The Shortcuts tab does not directly display database data.  Instead,
    # it contains tasks and task groups.
    name = _("Shortcuts")
    slug = "shortcuts"
    template_name = "dbaas_ui/shortcuts/_shortcuts_tab.html"


class DatabasePageTabs(tabs.TabGroup):
    slug = "database_page"
    # Database page has a welcome/main tab and several sub-tabs
    tabs = (ShortcutsTab,)
    show_single_tab = False
    sticky = True
