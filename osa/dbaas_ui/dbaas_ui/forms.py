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

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.templatetags import sizeformat

import logging

from trove_dashboard import api as trove_api


def parse_element_and_value_text(element_and_value):
    if element_and_value:
        element, element_value = element_and_value.split('::', 1)
        return element.strip(), element_value.strip()
    return None, None


def retrieve_instances(request, allowed_states=None):
    # Retrieve all instances whose status matches the allowed statuses
    # (return all instances if allowed_states is none)
    __method__ = 'forms.retrieve_instances'
    all_instances = []
    allowed_instances = []
    try:
        all_instances = trove_api.trove.instance_list(request)
    except Exception as e:
        logging.error("%s: Exception retrieving instances: %s", __method__, e)
        msg = _('Unable to retrieve list of instances.')
        exceptions.handle(request, msg)

    # Ensure we only return those instances that are in the allowed states
    if allowed_states:
        for instance in all_instances:
            if instance.status in allowed_states:
                allowed_instances.append(instance)
    else:
        allowed_instances = all_instances

    return allowed_instances


def create_instance_choices(request, allowed_states=None, instanceID=None):
    # build a list of instance choices filtered on a passed in
    # list of allowed statuses The choices have a value of the instance ID.
    instance_choices = []

    all_instances = retrieve_instances(request, allowed_states)

    if not instanceID:
        # Initial (and default) value instructs the user to select an instance
        instance_choices.append((None, _("Select an instance")))

    for instance in all_instances:
        # If an instance id was passed in
        if instanceID:
            # Then only append elements if the instance IDs match
            # (should only be one)
            if instance.id.startswith(instanceID):
                instance_choices.append((instance.id, instance.name))
        else:
            # No instance ID was passed in -- just append all instances
            instance_choices.append((instance.id, instance.name))

    # If nothing ended up getting added to the list of choices
    if len(instance_choices) == 0:
        # Should only occurs when an instance ID was passed in....
        instance_choices.append((None, _("Selected instance not available")))
        msg = _('Selected instance could not be retrieved.')
        messages.error(request, msg)

    return instance_choices


def create_inst_fl_choices(request, allowed_states=None, instanceID=None):
    # build a list of instance choices that also includes the current
    # flavor for that instance -- filtered on a passed in list of allowed
    # statuses.  The choices have a combined value of the instanc ID and
    # current flavor ID.
    __method__ = 'forms.create_inst_flavors_choices'
    instance_choices = []

    all_instances = retrieve_instances(request, allowed_states)

    if not instanceID:
        # Initial (and default) value instructs user to select an instance
        instance_choices.append((None, _("Select an instance")))

    for inst in all_instances:
        # start with empy flavor
        flavor = ""
        # initialize the displayValue for the instance (just instance name)
        displayValue = inst.name

        choiceValue = ""
        # If an instance id was passed in
        if instanceID:
            # Then only append elements if the instance IDs match
            # (should only be one)
            if inst.id.startswith(instanceID):
                # Try to retrieve the 'size' (flavor) for the instance.
                try:
                    flavor = trove_api.trove.flavor_get(request,
                                                        inst.flavor['id'])
                    # we got a flavor, so set displayValue for the instance to
                    # the instance name and current flavor information
                    nameVal = inst.name + ": " + flavor.name
                    sizeVal = sizeformat.mbformat(flavor.ram) + " RAM"
                    displayValue = nameVal + " | " + sizeVal
                    choiceValue = inst.id + "::" + str(flavor.id)
                    instance_choices.append((choiceValue, displayValue))
                except Exception as e:
                    logging.error("%s: Exception retrieving size information"
                                  " for instance: %s.  Exception is: %s",
                                  __method__, inst.name, e)
                    msg = _('Unable to retrieve size information for'
                            ' instance %s.',
                            inst.name)
                    exceptions.handle(request, msg)
        else:
            # No instance ID was passed in -- just append all instances
            # Try to retrieve the 'size' (flavor) for the instance.
            try:
                flavor = trove_api.trove.flavor_get(request, inst.flavor['id'])
                # we got a flavor, so set displayValue for the instance to the
                # instance name and current flavor information
                nameVal = inst.name + ": " + flavor.name
                sizeVal = sizeformat.mbformat(flavor.ram) + " RAM"
                displayValue = nameVal + " | " + sizeVal
                choiceValue = inst.id + "::" + str(flavor.id)
                instance_choices.append((choiceValue, displayValue))
            except Exception as e:
                logging.error("%s: Exception retrieving size information for"
                              " instance: %s.  Exception is: %s", __method__,
                              inst.name, e)
                msg = _('Unable to retrieve size information for instance %s.',
                        inst.name)
                exceptions.handle(request, msg)

    # If nothing ended up getting added to the list of choices
    if len(instance_choices) == 0:
        # Should only occurs when an instance ID was passed in....
        instance_choices.append((None, _("Selected instance not available")))
        msg = _('Selected instance could not be retrieved.')
        messages.error(request, msg)

    return instance_choices


def create_inst_vol_size_choices(request, allowed_states=None, instID=None):
    # build a list of instance choices that also includes the current volume
    # size for the instances -- filtered on a passed in list of allowed
    # statuses.  The choices have a combined value of the instance ID and
    # current volume size.
    instance_choices = []

    all_instances = retrieve_instances(request, allowed_states)

    if not instID:
        # Initial (and default) value instructs user to select an instance
        instance_choices.append((None, _("Select an instance")))

    for instance in all_instances:
        iSize = instance.volume['size']
        displayValue = instance.name + ':  ' + sizeformat.diskgbformat(iSize)
        choiceValue = instance.id + "::" + str(iSize)

        # If an instance id was passed in
        if instID:
            # Then only append elements if the instance IDs match
            # (should only be one)
            if instance.id.startswith(instID):
                instance_choices.append((choiceValue, displayValue))
        else:
            # No instance ID was passed in -- just append all instances
            instance_choices.append((choiceValue, displayValue))

    # If nothing ended up getting added to the list of choices
    if len(instance_choices) == 0:
        # Should only occurs when an instance ID was passed in....
        instance_choices.append((None, _("Selected instance not available")))
        msg = _('Selected instance could not be retrieved.')
        messages.error(request, msg)

    return instance_choices


def retrieve_flavors(request):
    # Retrieve all flavors
    __method__ = 'forms.retreive_flavors'
    all_flavors = []
    try:
        all_flavors = trove_api.trove.flavor_list(request)
    except Exception as e:
        logging.error("%s: Exception retrieving flavors: %s", __method__, e)
        msg = _('Unable to retrieve list of flavors.')
        exceptions.handle(request, msg)
    return all_flavors


def create_flavor_choices(request):
    # build a list of flavors choices
    flavor_choices = []
    # Initial (and default) value instructs user to select a flavor
    flavor_choices.append((None, _("Select a size")))

    all_flavors = retrieve_flavors(request)

    for flavor in all_flavors:
        sizeVal = sizeformat.mbformat(flavor.ram) + " RAM"
        displayValue = flavor.name + ":  " + sizeVal
        flavor_choices.append((flavor.id, displayValue))
    return flavor_choices


def retrieve_instance_name(request, instance_id):
    # Retrieve the name of an instance based on an instance id.
    # If the instance is not able to be retrieved, returns the instance_id
    __method__ = 'forms.retrieve_instance'

    instance_name = instance_id
    try:
        instance = trove_api.trove.instance_get(request, instance_id)
        instance_name = instance.name
    except Exception as e:
        logging.error("%s: Exception retrieving instance with ID: %s."
                      " Exception is: %s", __method__, instance_id, e)
        msg = ('Attempt to retrieve instance information for instance with'
               ' ID %(instance_id)s was not successful.  The selected'
               ' function is still being attempted.  Details of the'
               ' error: %(reason)s'
               % {'instance_id': instance_id, 'reason': e})
        exceptions.handle(request, msg)

    return instance_name


def retrieve_backup_name(request, backup_id):
    # Retrieve the name of an backup based on a backup id.
    # If the backup is not able to be retrieved, returns the backup_id
    __method__ = 'forms.retrieve_backup'

    backup_name = backup_id
    try:
        backup = trove_api.trove.backup_get(request, backup_id)
        backup_name = backup.name
    except Exception as e:
        logging.error("%s: Exception retrieving backup with ID: %s."
                      " Exception is: %s", __method__, backup_id, e)
        msg = ('Attempt to retrieve backup information for backup with'
               ' ID %(backup_id)s was not successful.  The selected function'
               ' is still being attempted.  Details of the error: %(reason)s'
               % {'backup_id': backup_id, 'reason': e})
        exceptions.handle(request, msg)

    return backup_name


def retrieve_datastores(request):
    # Retrieve all datastores
    __method__ = 'forms.retrieve_datastores'
    all_datastores = []
    try:
        all_datastores = trove_api.trove.datastore_list(request)
    except Exception as e:
        logging.error("%s: Exception retrieving datastores: %s", __method__, e)
        msg = _('Unable to retrieve list of datastores.')
        exceptions.handle(request, msg)

    return all_datastores


def retrieve_backups(request, allowed_states=None):
    # Retrieve all backups whose status matches the allowed statuses
    # (return all backups if allowed_states is none)
    __method__ = 'forms.retrieve_backups'
    all_backups = []
    allowed_backups = []
    try:
        all_backups = trove_api.trove.backup_list(request)
    except Exception as e:
        logging.error("%s: Exception retrieving backups: %s", __method__, e)
        msg = _('Unable to retrieve list of backups.')
        exceptions.handle(request, msg)

    # Ensure we only return those backups that are in the allowed states
    if allowed_states:
        for backup in all_backups:
            if backup.status in allowed_states:
                allowed_backups.append(backup)
    else:
        allowed_backups = all_backups

    return allowed_backups


def create_backup_choices(request, allowed_states=None, backupID=None):
    # build a list of backup choices filtered on a passed in
    # list of allowed statuses. The choices have a value of the backup ID.
    backup_choices = []

    all_backups = retrieve_backups(request, allowed_states)

    if not backupID:
        # Initial (and default) value instructs the user to select an instance
        backup_choices.append((None, _("Select a backup")))

    for backup in all_backups:
        # If an backup id was passed in
        if backupID:
            # Then only append elements if the backup IDs match
            # (should only be one)
            if backup.id.startswith(backupID):
                backup_choices.append((backup.id, backup.name))
        else:
            # No backup ID was passed in -- just append all backups
            backup_choices.append((backup.id, backup.name))

    # If nothing ended up getting added to the list of choices
    if len(backup_choices) == 0:
        # Should only occurs when a backup ID was passed in....
        backup_choices.append((None, _("Selected backup not available")))
        msg = _('Selected backup could not be retrieved.')
        messages.error(request, msg)

    return backup_choices


class RestartInstanceForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(
        label=_("Instance"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(RestartInstanceForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Restrict list of instances to those that can be restarted (statuses)
        sts = ("ACTIVE", "SHUTDOWN", "RESTART_REQUIRED")
        choices = create_instance_choices(request, sts, instID)

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance = self.data['instance']

        if not instance:
            msg = _("Select an instance to restart.")
            self._errors['instance'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.RestartInstanceForm.handle'

        selected_instance = data['instance']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance_name(request, selected_instance)

        # Perform the restart attempt
        try:
            trove_api.trove.instance_restart(request, selected_instance)
        except Exception as e:
            failure_message = ("Attempt to restart instance %(instance_name)s"
                               " was not successful.  Details of the"
                               " error: %(reason)s"
                               % {'instance_name': instance_name, 'reason': e})
            logging.error("%s: Exception received trying to restart"
                          " instance %s.  Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Instance %(instance_name)s was restarted.'
               % {'instance_name': instance_name})
        messages.success(request, msg)
        return True


class DeleteInstanceForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(
        label=_("Instance"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(DeleteInstanceForm, self).__init__(request, *args, **kwargs)

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        instID = None
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Allow all instances to be deleted (There are no status restrictions)
        sts = None
        choices = create_instance_choices(request, sts, instID)

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance = self.data['instance']

        if not instance:
            msg = _("Select an instance to delete.")
            self._errors['instance'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.DeleteInstanceForm.handle'

        selected_instance = data['instance']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance_name(request, selected_instance)

        # Perform the delete attempt
        try:
            trove_api.trove.instance_delete(request,
                                            selected_instance)
        except Exception as e:
            failure_message = ("Attempt to delete instance %(instance_name)s"
                               " was not successful.  Details of the error:"
                               " %(reason)s"
                               % {'instance_name': instance_name,
                                  'reason': e})
            logging.error("%s: Exception received trying to delete instance %s"
                          " Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Delete of instance %(instance_name)s started.'
               % {'instance_name': instance_name})
        messages.success(request, msg)
        return True


class ResizeInstanceForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(
        label=_("Instance and size"),
        required=True)
    new_flavor = forms.ChoiceField(label=_("New size"),
                                   help_text=_("Choose a new size for the"
                                               " selected instance."))

    def __init__(self, request, *args, **kwargs):
        super(ResizeInstanceForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Restrict those instances to those that can be resized
        sts = ("ACTIVE", "SHUTOFF", )
        instance_choices = create_inst_fl_choices(request, sts, instID)
        self.fields['instance'].choices = instance_choices
        self.fields['new_flavor'].choices = create_flavor_choices(request)

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance_and_flavor = self.data['instance']
        new_flavor = self.data['new_flavor']
        oldfl = None

        if not new_flavor:
            msg = _("Select a new size")
            self._errors['new_flavor'] = self.error_class([msg])

        if not instance_and_flavor:
            msg = _("Select an instance and size")
            self._errors['instance'] = self.error_class([msg])
        else:
            sel, oldfl = parse_element_and_value_text(self.data['instance'])

        if oldfl and new_flavor:
            if oldfl == new_flavor:
                msg = _("Select a new size that is not the same as"
                        " the old size.")
                self._errors['new_flavor'] = self.error_class([msg])

        # TODO:  Consider -- should we allow the user to resize an instance
        #        'down' -- for example, if an instance is at a large size,
        #        can user resize that instance to medium size?

    def handle(self, request, data):
        __method__ = 'forms.ResizeInstanceForm.handle'

        selected_inst, oldfl = parse_element_and_value_text(data['instance'])

        new_flavor = data['new_flavor']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance_name(request, selected_inst)

        # Perform the resize instance attempt
        try:
            trove_api.trove.instance_resize(request,
                                            selected_inst,
                                            new_flavor)
        except Exception as e:
            failure_message = ("Attempt to resize instance %(instance_name)s"
                               " was not successful.  Details of the"
                               " error: %(reason)s"
                               % {'instance_name': instance_name, 'reason': e})
            logging.error("%s: Exception received trying to resize instance %s"
                          " Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Resize of instance %(instance_name)s started.'
               % {'instance_name': instance_name})
        messages.success(request, msg)
        return True


class ResizeVolumeForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(
        label=_("Instance and volume size"),
        required=True)

    new_size = forms.IntegerField(label=_("New volume size (GB)"),
                                  initial=1,
                                  min_value=0)

    def __init__(self, request, *args, **kwargs):
        super(ResizeVolumeForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Restrict those instances to those whose volumes can be resized
        sts = ("ACTIVE",)
        choices = create_inst_vol_size_choices(request, sts, instID)

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance_and_size = self.data['instance']
        new_size = self.data['new_size']
        old_size = None

        if not new_size:
            msg = _("Select a new volume size that is greater than"
                    " the existing size.")
            self._errors['new_size'] = self.error_class([msg])

        if not instance_and_size:
            msg = _("Select an instance and volume size")
            self._errors['instance'] = self.error_class([msg])
        else:
            sel, old_size = parse_element_and_value_text(self.data['instance'])

        if old_size and new_size:
            if new_size <= old_size:
                msg = _("Select a new volume size that is greater"
                        " than the existing size.")
                self._errors['new_size'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.ResizeVolumeForm.handle'

        selected_inst, oldsize = parse_element_and_value_text(data['instance'])
        new_size = data['new_size']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance_name(request, selected_inst)

        # Perform the resize volume attempt
        try:
            trove_api.trove.instance_resize_volume(request,
                                                   selected_inst,
                                                   new_size)
        except Exception as e:
            failure_message = ("Attempt to resize volume for instance"
                               " %(instance_name)s was not successful."
                               "  Details of the error: %(reason)s"
                               % {'instance_name': instance_name, 'reason': e})
            logging.error("%s: Exception received trying to resize volume for"
                          " instance %s.  Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Resize volume for instance %(instance_name)s started.'
               % {'instance_name': instance_name})
        messages.success(request, msg)
        return True


class CreateBackupForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=80, label=_("Backup Name"))
    description = forms.CharField(max_length=80,
                                  label=_("Backup Description"),
                                  required=False,)

    instance = forms.ChoiceField(
        label=_("Instance"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(CreateBackupForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Restrict list of instances to those that can be restarted (statuses)
        sts = ("ACTIVE",)
        choices = create_instance_choices(request, sts, instID)

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance = self.data['instance']

        if not instance:
            msg = _("Select an instance to back up")
            self._errors['instance'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.CreateBackupForm.handle'

        selected_instance = data['instance']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance_name(request, selected_instance)

        # Perform the backup attempt
        try:
            trove_api.trove.backup_create(request, data['name'],
                                          selected_instance,
                                          data['description'])
        except Exception as e:
            failure_message = ("Attempt to create backup %(backup_name)s of"
                               " instance %(instance_name)s was not"
                               " successful.  Details of the error: %(reason)s"
                               % {'backup_name': data['name'], 'instance_name':
                                  instance_name, 'reason': e})
            logging.error("%s: Exception received trying to create backup for"
                          " instance %s.  Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Backup %(backup_name)s of instance %(instance_name)s started.'
               % {'backup_name': data['name'], 'instance_name': instance_name})
        messages.success(request, msg)
        return True


class RenameInstanceForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(
        label=_("Instance"),
        required=True)

    name = forms.CharField(max_length=80, label=_("New Name"))

    def __init__(self, request, *args, **kwargs):
        super(RenameInstanceForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Allow all instances to be renamed
        sts = None
        choices = create_instance_choices(request, sts, instID)

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance = self.data['instance']

        if not instance:
            msg = _("Select an instance to rename")
            self._errors['instance'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.RenameInstance.handle'

        sel_inst = data['instance']
        new_name = data['name']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance_name(request, sel_inst)

        # Perform the instance rename attempt
        try:
            trove_api.trove.troveclient(request).instances.edit(sel_inst,
                                                                name=new_name)
        except Exception as e:
            failure_message = ("Attempt to rename instance %(old_name)s to"
                               " new name %(new_name)s was not"
                               " successful.  Details of the error: %(reason)s"
                               % {'old_name': instance_name, 'new_name':
                                  new_name, 'reason': e})
            logging.error("%s: Exception received trying to rename"
                          " instance %s.  Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Instance %(instance_name)s was renamed to %(new_name)s.'
               % {'instance_name': instance_name, 'new_name': new_name})

        messages.success(request, msg)
        return True


class DeleteBackupForm(forms.SelfHandlingForm):
    backup = forms.ChoiceField(
        label=_("Backup"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(DeleteBackupForm, self).__init__(request, *args, **kwargs)

        backupID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'backup_id' in kwargs['initial']:
                backupID = kwargs['initial']['backup_id']

        # Allow all backups to be deleted (there are no status restrictions)
        sts = None
        choices = create_backup_choices(request, sts, backupID)

        self.fields['backup'].choices = choices

        if backupID:
            self.fields['backup'].initial = backupID
            self.fields['backup'].widget.attrs['readonly'] = True

    def clean(self):
        backup = self.data['backup']

        if not backup:
            msg = _("Select an backup to delete.")
            self._errors['backup'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.DeleteBackupForm.handle'

        selected_backup = data['backup']

        # Need the backup name in both success/failure cases.
        # Retrieve it now (will be backup_id if we couldn't retrieve it).
        backup_name = retrieve_backup_name(request, selected_backup)

        # Perform the delete attempt
        try:
            trove_api.trove.backup_delete(request, selected_backup)
        except Exception as e:
            failure_message = ("Attempt to delete backup %(backup_name)s was"
                               " not successful.  Details of the error:"
                               "  %(reason)s"
                               % {'backup_name': backup_name, 'reason': e})
            logging.error("%s: Exception received trying to delete backup %s"
                          " Exception is: %s",
                          __method__, backup_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Delete of backup %(backup_name)s started.'
               % {'backup_name': backup_name})
        messages.success(request, msg)
        return True
