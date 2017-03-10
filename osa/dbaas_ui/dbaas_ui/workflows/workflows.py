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
import binascii
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from horizon import workflows
from openstack_dashboard import api as dash_api
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.project.instances.workflows \
    import create_instance as dash_create_instance


from trove_dashboard import api as trove_api

LOG = logging.getLogger(__name__)


def parse_datastore_and_version_text(datastore_and_version):
    if datastore_and_version:
        datastore, datastore_version = datastore_and_version.split('-', 1)
        return datastore.strip(), datastore_version.strip()
    return None, None


class SetInstanceDetailsAction(workflows.Action):
    # Hide availability zone (but keep it so we have a value to retrieve)
    availability_zone = forms.ChoiceField(
        label=_("Availability Zone"),
        widget=forms.HiddenInput(),           # Hide availability zone for now
        required=False)
    name = forms.CharField(max_length=80, label=_("Instance Name"))
    volume = forms.IntegerField(label=_("Volume Size"),
                                min_value=0,
                                initial=1,
                                help_text=_("Size of the volume in GB."))
    datastore = forms.ChoiceField(
        label=_("Datastore"),
        help_text=_("Type and version of datastore."),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'datastore'
        }))

    class Meta(object):
        name = _("Details")
        help_text_template = "project/databases/_launch_details_help.html"

    def clean(self):
        datastore_and_version = self.data.get("datastore", None)
        if not datastore_and_version:
            msg = _("You must select a datastore type and version.")
            self._errors["datastore"] = self.error_class([msg])
        else:
            datastore, datastore_version = parse_datastore_and_version_text(
                binascii.unhexlify(datastore_and_version))
            field_name = self._build_flavor_field_name(datastore,
                                                       datastore_version)
            flavor = self.data.get(field_name, None)
            if not flavor:
                msg = _("You must select a flavor.")
                self._errors[field_name] = self.error_class([msg])
        return self.cleaned_data

    def handle(self, request, context):
        datastore_and_version = context["datastore"]
        if datastore_and_version:
            datastore, datastore_version = parse_datastore_and_version_text(
                binascii.unhexlify(context["datastore"]))
            field_name = self._build_flavor_field_name(datastore,
                                                       datastore_version)
            flavor = self.data[field_name]
            if flavor:
                context["flavor"] = flavor
                return context
        return None

    @memoized.memoized_method
    def availability_zones(self, request):
        try:
            return dash_api.nova.availability_zone_list(request)
        except Exception:
            LOG.exception("Exception while obtaining availablity zones")
            self._availability_zones = []

    def populate_availability_zone_choices(self, request, context):
        try:
            zones = self.availability_zones(request)
        except Exception:
            zones = []
            redirect = reverse('horizon:project:databases:index')
            exceptions.handle(request,
                              _('Unable to retrieve availability zones.'),
                              redirect=redirect)

        zone_list = [(zone.zoneName, zone.zoneName)
                     for zone in zones if zone.zoneState['available']]
        zone_list.sort()
        if not zone_list:
            zone_list.insert(0, ("", _("No availability zones found")))
        elif len(zone_list) > 1:
            zone_list.insert(0, ("", _("Any Availability Zone")))
        return zone_list

    @memoized.memoized_method
    def datastore_flavors(self, request, datastore_name, datastore_version):
        try:
            return trove_api.trove.datastore_flavors(
                request, datastore_name, datastore_version)
        except Exception:
            LOG.exception("Exception while obtaining flavors list")
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(request,
                              _('Unable to obtain flavors.'),
                              redirect=redirect)

    @memoized.memoized_method
    def datastores(self, request):
        try:
            return trove_api.trove.datastore_list(request)
        except Exception:
            LOG.exception("Exception while obtaining datastores list")
            self._datastores = []

    @memoized.memoized_method
    def datastore_versions(self, request, datastore):
        try:
            return trove_api.trove.datastore_version_list(request, datastore)
        except Exception:
            LOG.exception("Exception while obtaining datastore version list")
            self._datastore_versions = []

    def populate_datastore_choices(self, request, context):
        choices = ()
        datastores = self.datastores(request)
        if datastores is not None:
            for ds in datastores:
                versions = self.datastore_versions(request, ds.name)
                if versions:
                    # only add to choices if datastore has at least one version
                    version_choices = ()
                    for v in versions:
                        if hasattr(v, 'active') and not v.active:
                            continue
                        selection_text = self._build_datastore_display_text(
                            ds.name, v.name)
                        widget_text = self._build_widget_field_name(
                            ds.name, v.name)
                        version_choices = (version_choices +
                                           ((widget_text, selection_text),))
                        self._add_datastore_flavor_field(request,
                                                         ds.name,
                                                         v.name)
                    choices = choices + version_choices
        return choices

    def _add_datastore_flavor_field(self,
                                    request,
                                    datastore,
                                    datastore_version):
        name = self._build_widget_field_name(datastore, datastore_version)
        attr_key = 'data-datastore-' + name
        field_name = self._build_flavor_field_name(datastore,
                                                   datastore_version)
        self.fields[field_name] = forms.ChoiceField(
            label=_("Flavor"),
            help_text=_("Size of image to launch."),
            required=False,
            widget=forms.Select(attrs={
                'class': 'switched',
                'data-switch-on': 'datastore',
                attr_key: _("Flavor")
            }))
        valid_flavors = self.datastore_flavors(request,
                                               datastore,
                                               datastore_version)
        if valid_flavors:
            self.fields[field_name].choices = instance_utils.sort_flavor_list(
                request, valid_flavors)

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_widget_field_name(self, datastore, datastore_version):
        # Since the fieldnames cannot contain an uppercase character
        # we generate a hex encoded string representation of the
        # datastore and version as the fieldname
        return binascii.hexlify(
            self._build_datastore_display_text(datastore, datastore_version))

    def _build_flavor_field_name(self, datastore, datastore_version):
        return self._build_widget_field_name(datastore,
                                             datastore_version)

TROVE_ADD_USER_PERMS = getattr(settings, 'TROVE_ADD_USER_PERMS', [])
TROVE_ADD_DATABASE_PERMS = getattr(settings, 'TROVE_ADD_DATABASE_PERMS', [])
TROVE_ADD_PERMS = TROVE_ADD_USER_PERMS + TROVE_ADD_DATABASE_PERMS


class SetInstanceDetails(workflows.Step):
    action_class = SetInstanceDetailsAction
    contributes = ("name", "volume", "flavor", "datastore",
                   "availability_zone")


class AdvancedAction(workflows.Action):
    backup = forms.ChoiceField(
        label=_('Backup Name'),
        required=True,
        help_text=_('Select a backup to restore'),)

    class Meta(object):
        name = _("Advanced")
        help_text_template = "project/database/_launch_advanced_help.html"

    def populate_backup_choices(self, request, context):
        try:
            backups = trove_api.trove.backup_list(request)
            choices = [(b.id, b.name) for b in backups
                       if b.status == 'COMPLETED']
        except Exception:
            choices = []

        if choices:
            choices.insert(0, (None, _("Select backup")))
        else:
            choices.insert(0, (None, _("No backups available")))
        return choices

    def clean(self):
        cleaned_data = super(AdvancedAction, self).clean()

        try:
            backup = cleaned_data['backup']
            if backup:
                try:
                    bkup = trove_api.trove.backup_get(self.request, backup)
                    self.cleaned_data['backup'] = bkup.id
                except Exception:
                    raise forms.ValidationError(_("No backups found."))
            else:
                raise forms.ValidationError(_("Select a backup."))
        except Exception:
            raise forms.ValidationError(_("Select a backup."))

        return cleaned_data


class Advanced(workflows.Step):
    action_class = AdvancedAction
    contributes = ['backup']


class LaunchInstance(workflows.Workflow):
    slug = "launch_instance"
    name = _("Launch Instance")
    finalize_button_name = _("Launch")
    success_message = _('Launched %(count)s named "%(name)s".')
    failure_message = _('Unable to launch %(count)s named "%(name)s".')
    success_url = "horizon:project:database:index"
    default_steps = (SetInstanceDetails,
                     dash_create_instance.SetNetwork)

    def __init__(self, request=None, context_seed=None, entry_point=None,
                 *args, **kwargs):
        super(LaunchInstance, self).__init__(request, context_seed,
                                             entry_point, *args, **kwargs)
        self.attrs['autocomplete'] = (
            settings.HORIZON_CONFIG.get('password_autocomplete'))

    def get_success_url(self):
        # On completion, ensure we navigate to the instances tab
        tgtTab = '?tab=database_page__instances'
        return reverse('horizon:project:database:index') + tgtTab

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown instance')
        return message % {"count": _("instance"), "name": name}

    def _get_nics(self, context):
        netids = context.get('network_id', None)
        if netids:
            return [{"net-id": netid, "v4-fixed-ip": ""}
                    for netid in netids]
        else:
            return None

    def _get_backup(self, context):
        # By default this launch instance will not supply a "backup" -- this
        # can be overridden to return a real value
        return None

    def handle(self, request, context):
        try:
            datastore, ds_version = parse_datastore_and_version_text(
                binascii.unhexlify(self.context['datastore']))

            volume_type = None
            locality = None
            config = None
            databases = None
            users = None
            replica_of = None
            replica_count = None
            avail_zone = None
            backup = self._get_backup(context)
            logging.debug("Launching database instance with parameters "
                          "{name=%s, volume=%s, volume_type=%s, flavor=%s, "
                          "datastore=%s, datastore_version=%s, "
                          "dbs=%s, users=%s, "
                          "backups=%s, nics=%s, "
                          "replica_of=%s replica_count=%s, "
                          "configuration=%s, locality=%s, "
                          "availability_zone=%s}",
                          context['name'], context['volume'],
                          volume_type, context['flavor'],
                          datastore, ds_version,
                          databases, users,
                          backup, self._get_nics(context),
                          replica_of, replica_count,
                          config, locality,
                          avail_zone)
            trove_api.trove.instance_create(request,
                                            context['name'],
                                            context['volume'],
                                            context['flavor'],
                                            datastore=datastore,
                                            datastore_version=ds_version,
                                            databases=databases,
                                            users=users,
                                            restore_point=backup,
                                            nics=self._get_nics(context),
                                            replica_of=replica_of,
                                            replica_count=replica_count,
                                            volume_type=volume_type,
                                            configuration=config,
                                            locality=locality,
                                            availability_zone=avail_zone)
            return True
        except Exception:
            exceptions.handle(request)
            return False


class RestoreFromBackup(LaunchInstance):
    # This function is really a 'launch instance' -- but we've added the
    # requirement to supply the backup which we're using as an initial state.
    # User still needs to provide certain information: for example, name,
    # datastore, and so on
    slug = "restore_from_instance"
    name = _("Restore Database Instance From Backup")
    finalize_button_name = _("Restore")
    default_steps = (SetInstanceDetails,
                     dash_create_instance.SetNetwork, Advanced)

    def _get_backup(self, context):
        backup = None
        if context.get('backup'):
            backup = {'backupRef': context['backup']}
        return backup
