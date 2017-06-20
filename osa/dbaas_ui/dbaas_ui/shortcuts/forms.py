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
from horizon import forms
from horizon import messages
from horizon.templatetags import sizeformat
from horizon.utils import validators

import logging

from dbaas_ui.shortcuts import db_capability

from trove_dashboard import api as trove_api


def parse_element_and_value_text(element_and_value):
    # Parses a string of element/values in the form:
    # xx::yy -- we don't care what is in yy (so you are
    # allowed to nest an element/value combination within
    # the value of an element/value -- thus
    # xx::yy::zz is allowed -- we'll just return:
    # xx and yy::zz.)
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

    if instanceID:
        all_instances = [retrieve_instance(request, instanceID)]
    else:
        all_instances = retrieve_instances(request, allowed_states)
        # Initial (and default) choice instructs the user to select an instance
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
                    msg = ('Unable to retrieve size information for'
                           ' instance %s.', inst.name)
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
                msg = ('Unable to retrieve size information for '
                       'instance %s.', inst.name)
                exceptions.handle(request, msg)

    # If nothing ended up getting added to the list of choices
    if len(instance_choices) == 0:
        # Should only occurs when an instance ID was passed in....
        instance_choices.append((None, _("Selected instance not available")))
        msg = _('Selected instance could not be retrieved.')
        messages.error(request, msg)

    return instance_choices


def create_inst_type_choices(request, allowed_states=None, instanceID=None):
    # build a list of instance choices that also includes the instance
    # type for that instance -- filtered on a passed in list of allowed
    # statuses.  The choices have a combined value of the instanc ID and
    # instance type.
    instance_choices = []

    all_instances = retrieve_instances(request, allowed_states)

    if not instanceID:
        # Initial (and default) value instructs user to select an instance
        instance_choices.append((None, _("Select an instance")))

    for inst in all_instances:
        # initialize the displayValue for the instance (just instance name)
        displayValue = inst.name
        choiceValue = inst.id + "::" + inst.datastore['type']
        # If an instance id was passed in
        if instanceID:
            # Then only append elements if the instance IDs match
            # (should only be one)
            if inst.id.startswith(instanceID):
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


def create_db_instance_choices(request,
                               instanceID=None):
    # builds a database instance choice that also includes the current
    # version for that database.
    # The choice has a combined value of the instanc ID,
    # database, and current flavor ID.
    instance_choices = []

    if instanceID:
        all_instances = [retrieve_instance(request, instanceID)]

    for inst in all_instances:
        displayValue = inst.name + \
            " (" + inst.datastore['type'] + \
            "):  Version: " + inst.datastore['version']
        choiceValue = inst.id

        # If an instance id was passed in
        if instanceID:
            # Then only append elements if the instance IDs match
            # (should only be one)
            if inst.id.startswith(instanceID):
                    instance_choices.append((choiceValue, displayValue))

    # If nothing ended up getting added to the list of choices
    if len(instance_choices) == 0:
        # Should only occurs when an instance ID was passed in....
        instance_choices.append((None, _("Selected instance not available")))
        msg = _('Selected instance could not be retrieved.')
        messages.error(request, msg)

    if instanceID:
        return instance_choices, all_instances


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


def retrieve_users(request, instance_id):
    # Retrieve all users for the instance_id passed in
    __method__ = 'forms.retrieve_users'
    all_users = []
    try:
        all_users = trove_api.trove.users_list(request, instance_id)
    except Exception as e:
        # Retrieve the instance so we can display that information on our
        # error message -- so the user knows which instance is having
        # issues retrieving user information.
        instance = retrieve_instance(request, instance_id)

        logging.error("%s: Exception retrieving users for instance %s.  "
                      "Error is: %s", __method__, instance.name, e)

        msg = ('Unable to retrieve list of users for '
               'instance %s.' % instance.name)
        exceptions.handle(request, msg)

    return all_users


def create_user_choices(request, instance_id=None, userName=None):
    # build a list of user choices for the instance passed in, and
    # then filter that list on a passed in userName
    user_choices = []
    all_instances = []

    # Set initial value if needed
    if not userName:
        # Initial (and default) value instructs the user to select a user
        user_choices.append((None, _("Select a user")))

    # Retrieve the instances (either the one identified by instance_id, or
    # all instances
    if instance_id:
        # Retrieve the specific instance
        all_instances.append(retrieve_instance(request, instance_id))
    else:
        # Retrieve all instances
        all_instances = retrieve_instances(request)

    # all_instances may be empty if no instances have been defined.
    for instance in all_instances:
        all_users = retrieve_users(request, instance.id)

        for user in all_users:
            # value will be the instance id and the user name
            choiceValue = instance.id + "::" + user.name

            if not instance_id:
                # We were called without an instance context --we can go ahead
                # and add the instance name to the user name for the display
                # value, and append this user entry to our list of choices
                displayValue = user.name + " (instance: " + instance.name + ')'
            else:
                # We already have the instance context -- don't need to append
                # the instance name to the user name for the display value
                displayValue = user.name

            # If we were not called with a user name, or we were called with
            # a user name and the retrieved user's name matches the user
            # name passed in, we can append this user entry to our list
            # of choices.
            if not userName or userName == user.name:
                user_choices.append((choiceValue, displayValue))

    # If nothing ended up getting added to the list of choices
    if len(user_choices) == 0:
        if userName:
            user_choices.append((None, _("Selected user not available")))
            msg = _('Selected user could not be retrieved.')
            messages.error(request, msg)
        else:
            # No users exist -- shouldn't happen (we should have a
            # default value...very strange...just put on a 'no users
            # available' message
            user_choices.append((None, _("No users available")))
    elif len(user_choices) == 1:
        if not userName:
            # We were called without a user name, and there's only a single
            # element in our list.  In this scenario, we put in a default
            # value on telling the user to select a item...but there's
            # nothing there -- remove the 'select a user' default value
            # and add a 'no users available' message.
            user_choices.pop()
            user_choices.append((None, _("No users available")))

    return user_choices


def retrieve_databases(request, instance_id):
    # Retrieve all databases for the instance_id passed in
    __method__ = 'forms.retrieve_databases'
    all_databases = []
    try:
        all_databases = trove_api.trove.database_list(request, instance_id)
    except Exception as e:
        # Retrieve the instance so we can display that information on our
        # error message -- so the user knows which instance is having
        # issues retrieving database information.
        instance = retrieve_instance(request, instance_id)

        logging.error("%s: Exception retrieving databases for instance %s.  "
                      "Error is: %s", __method__, instance.name, e)

        msg = ('Unable to retrieve list of databases for '
               'instance %s.' % instance.name)

        exceptions.handle(request, msg)

    return all_databases


def create_database_choices(request, instance_id=None, databaseName=None):
    # build a list of database choices for the instance passed in, and
    # then filter that list on a passed in databaseName
    database_choices = []
    all_instances = []

    if not databaseName:
        # Currently we only want the default ('Select a database')
        # added to our choices when we have NO dbName and no
        # instance ID
        if not instance_id:
            # Initial (and default) value instructs the user to
            # select a database
            database_choices.append((None, _("Select a database")))

    if (instance_id):
        # Retrieve the specific instance
        all_instances.append(retrieve_instance(request, instance_id))
    else:
        # Retrieve all instances
        all_instances = retrieve_instances(request)

    # all_instances may be empty of no instances have been defined.
    for instance in all_instances:
        all_databases = retrieve_databases(request, instance.id)

        for database in all_databases:
            # value will be the instance id and the database name
            choiceValue = instance.id + "::" + database.name

            if not instance_id:
                # We were called without an instance context --we can go ahead
                # and add the instance name to the database name for the
                # display value, and append this database entry to our list of
                # choices
                instPart = " (instance: " + instance.name + ')'
                displayValue = database.name + instPart
            else:
                # We already have the instance context -- don't need to append
                # the instance name to the database name for the display value
                displayValue = database.name

            # If we were not called with a database name, or we were called
            # with a database name and the retrieved database's name matches
            # the database name passed in, we can append this database entry
            # to our list of choices.
            if not databaseName or databaseName == database.name:
                database_choices.append((choiceValue, displayValue))

    # If nothing ended up getting added to the list of choices
    if len(database_choices) == 0:
        if databaseName:
            database_choices.append((None,
                                     _("Selected database not available")))
            msg = _('Selected database could not be retrieved.')
            messages.error(request, msg)
        else:
            # No databases exist -- shouldn't happen (we should have a
            # default value...very strange...just put on a 'no databases
            # available' message
            database_choices.append((None, _("No databases available")))
    elif len(database_choices) == 1:
        if not databaseName and not instance_id:
            # We were called without a database name, and without an instance.
            # There's only a single element on the list.  In this scenario,
            # we put in a default value on telling the user to select a item.
            # BUT there's nothing there -- remove the 'select a database'
            # default value and add a 'no databases available' message.
            database_choices.pop()
            database_choices.append((None, _("No databases available")))

    return database_choices


def retrieve_instance(request, instance_id):
    # Retrieve an instance based on an instance id.
    # If the instance is not able to be retrieved, returns None
    __method__ = 'forms.retrieve_instance'

    instance = None
    try:
        instance = trove_api.trove.instance_get(request, instance_id)
        return instance
    except Exception as e:
        logging.error("%s: Exception retrieving instance with ID: %s."
                      " Exception is: %s", __method__, instance_id, e)
        msg = ('Attempt to retrieve instance information for instance with'
               ' ID %(instance_id)s was not successful.  The selected'
               ' function is still being attempted.  Details of the'
               ' error: %(reason)s'
               % {'instance_id': instance_id, 'reason': e})
        exceptions.handle(request, msg)

    return instance


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
        instance_name = retrieve_instance(request, selected_instance).name

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
        instance_name = retrieve_instance(request, selected_instance).name

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

        # TODO(jdwald):  Consider -- should we allow the user to resize an
        #                instance 'down' -- for example, if an instance is
        #                at a large size, can user resize that instance to
        #                medium size?

    def handle(self, request, data):
        __method__ = 'forms.ResizeInstanceForm.handle'

        selected_inst, oldfl = parse_element_and_value_text(data['instance'])

        new_flavor = data['new_flavor']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance(request, selected_inst).name

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
        instance_name = retrieve_instance(request, selected_inst).name

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


class UpgradeInstanceForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(
        label=_("Database Instance and Version"),
        required=True)

    version = forms.ChoiceField(label=_("Available Versions"))

    orig_version = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, request, *args, **kwargs):
        __method__ = "forms.UpgradeInstanceForm.__init__"
        super(UpgradeInstanceForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']
            # if instID is none, check data to see if it is set
            if instID is None:
                instID = kwargs['data']['instance']

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

        # find instance associated with instance id
        instance_choices, instances = create_db_instance_choices(
            request,
            instanceID=instID)
        self.fields['instance'].choices = instance_choices

        for inst in instances:
            # Populate field with choices
            version_choices = []
            try:
                # Retrieve the available datastore versions
                ds_versions = trove_api.trove.datastore_version_list(
                    request,
                    inst.datastore['type'])
            except Exception as e:
                logging.error("%s: Exception received trying to retrieve "
                              "datastore versions for datastore %s. "
                              "Exception is: %s", __method__,
                              inst.datastore['type'], e)

            orig_version = inst.datastore['version']

            for avail_version in ds_versions:
                if avail_version.name > orig_version:
                    version_choices.append((avail_version.name,
                                            avail_version.name))

            if len(version_choices) >= 1:
                self.fields['version'].choices = version_choices
            else:
                msg = _("No newer database versions are available")
                self.fields['version'].choices = [(None, msg)]

            self.fields['orig_version'].initial = orig_version

    def clean(self):
        selected_version = self.data['version']

        if not selected_version:
            msg = _("Select an version to upgrade.")
            self._errors['version'] = self.error_class([msg])

        orig_version = self.data['orig_version']

        if selected_version <= orig_version:
            msg = _("Select a version that is newer than the current version.")
            self._errors['version'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.UpgradeInstanceForm.handle'

        selected_instance = data['instance']
        selected_version = data['version']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).

        instance_name = retrieve_instance(request, selected_instance).name

        # Perform the resize instance attempt
        try:
            trove_api.trove.troveclient(request).instances.upgrade(
                selected_instance,
                selected_version)

        except Exception as e:
            failure_message = ("Attempt to upgrade instance %(instance_name)s"
                               " was not successful.  Details of the"
                               " error: %(reason)s"
                               % {'instance_name': instance_name, 'reason': e})
            logging.error("%s: Exception received trying to upgrade "
                          "instance %s Exception is: %s",
                          __method__, instance_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Upgrading instance %(instance_name)s started.'
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

    parent = forms.ChoiceField(label=_("Parent Backup"),
                               required=False,
                               help_text=_("Optional parent backup"))

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

        # at this point, allow any backup to be a parent
        sts = None
        parent_choices = create_backup_choices(request)

        self.fields['parent'].choices = parent_choices

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
        instance_name = retrieve_instance(request, selected_instance).name

        # Perform the backup attempt
        try:
            trove_api.trove.backup_create(request, data['name'],
                                          selected_instance,
                                          data['description'],
                                          data['parent'])
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
        instance_name = retrieve_instance(request, sel_inst).name

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


class CreateUserForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"))
    password = forms.RegexField(
        label=_("Password"),
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    instance = forms.ChoiceField(
        label=_("Instance"),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'instance'
        }),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(CreateUserForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Restrict list of instances to those on which a user can
        # be added (based on instance statuses)
        sts = ("ACTIVE",)
        choices = create_inst_type_choices(request, sts, instID)

        new_list = []
        for choice in choices:
            if choice[0] is None:
                new_list.append((choice[0], choice[1]))
                continue
            instID, inst_type = parse_element_and_value_text(choice[0])
            if (db_capability.can_support_users(inst_type)):
                new_list.append((choice[0], choice[1]))

        choices = new_list

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

        database_choices = []

        for instance_choice in choices:
            # Retrieve the list of databases
            if instance_choice[0]:
                instanceID, inst_type = parse_element_and_value_text(
                    instance_choice[0])

                # Define a db field for this instance
                dataKey = 'data-instance-' + instance_choice[0]

                self.fields[instance_choice[0]] = forms.MultipleChoiceField(
                    label=_("Available Databases"),
                    required=False,
                    widget=forms.CheckboxSelectMultiple(
                        attrs={'class': 'switched',
                               'data-switch-on': 'instance',
                               dataKey: instance_choice[0]}))

                # Retrieve all databases for the instance
                database_choices = create_database_choices(request,
                                                           instanceID,
                                                           None)

                if len(database_choices) >= 1:
                    self.fields[instance_choice[0]].choices = database_choices
                else:
                    msg = _("No databases found")
                    self.fields[instance_choice[0]].choices = [(None, msg)]

    def clean(self):
        cleaned_data = super(CreateUserForm, self).clean()

        if 'instance' not in cleaned_data:
            msg = _("Select the instance on which to create the user.")
            self._errors['instance'] = self.error_class([msg])
        else:
            selected_instance, inst_type = parse_element_and_value_text(
                self.data['instance'])
            selected_databases = self.cleaned_data[
                self.data['instance']]
            # If it is a mongo database for the instance and no database
            # is selected, alert the user to select atleast one database.
            if (db_capability.create_user_requires_database(inst_type) and
                    len(selected_databases) == 0):
                msg = _("Select at least one database to create the user in.")
                self._errors[self.data['instance']] = self.error_class([msg])

        return cleaned_data

    def handle(self, request, data):
        __method__ = 'forms.createUserForm.handle'

        selected_instance, inst_type = parse_element_and_value_text(
            data['instance'])
        user_name = data['name']

        # Get the list of databases to which the new user should be
        # granted access (and put it into a form that's usable)
        selected_databases = data[data['instance']]
        dbs = []
        if len(selected_databases):
            for database in selected_databases:
                if database != "None":
                    inst_id, db_name = parse_element_and_value_text(database)
                    dbs.append({'name': db_name.strip()})

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance(request, selected_instance).name

        # Perform the create user attempt
        try:
            trove_api.trove.user_create(
                request,
                selected_instance,
                user_name,
                data['password'],
                host=None,
                databases=dbs)

        except Exception as e:
            failure_message = ("Attempt to create user %(user_name)s "
                               "on %(instance_name)s was not successful.  "
                               "Details of the error: %(reason)s"
                               % {'user_name': user_name,
                                  'instance_name': instance_name,
                                  'reason': e})
            logging.error("%s: Exception received trying to create "
                          "user %s.  Exception is: %s",
                          __method__, user_name, e)

            redirect = reverse("horizon:dbaas_ui:instances:detail",
                               args=(selected_instance,))
            redirect += "?tab=instance_details__users_tab"
            exceptions.handle(request, failure_message, redirect=redirect)
            return True

        msg = ("User %(user_name)s created on instance %(instance_name)s."
               % {'user_name': user_name, 'instance_name': instance_name})

        messages.success(request, msg)

        # We are successful -- store away the instance_id onto the session
        # so that we can correctly update our view.
        if hasattr(request, 'session'):
            request.session['instance_id'] = selected_instance

        return True


class DeleteUserForm(forms.SelfHandlingForm):
    user = forms.ChoiceField(
        label=_("User"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(DeleteUserForm, self).__init__(request, *args, **kwargs)

        selectedUser = None

        instance_id = None
        user_name = None

        choices = None

        # If an initial user id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'user_id' in kwargs['initial']:
                selectedUser = kwargs['initial']['user_id']
                instance_id, user_name = parse_element_and_value_text(
                    selectedUser)
                choices = create_user_choices(request, instance_id, user_name)
            elif 'data' in kwargs:
                if 'user' in kwargs['data']:
                    selectedUser = kwargs['data']['user']
                    instance_id, user_name = parse_element_and_value_text(
                        selectedUser)
                    choices = create_user_choices(request,
                                                  instance_id,
                                                  user_name)
                else:
                    choices = create_user_choices(request, None, None)
            else:
                choices = create_user_choices(request, None, None)
        else:
            choices = create_user_choices(request, None, None)

        self.fields['user'].choices = choices

        if selectedUser:
            self.fields['user'].initial = selectedUser
            self.fields['user'].widget.attrs['readonly'] = True

    def handle(self, request, data):
        __method__ = 'forms.DeleteUserForm.handle'

        instance_id, user_name = parse_element_and_value_text(
            self.data['user'])

        # Perform the delete attempt
        try:
            trove_api.trove.user_delete(request, instance_id, user_name)
        except Exception as e:
            failure_message = ("Attempt to delete user %(user_name)s was"
                               " not successful.  Details of the error:"
                               "  %(reason)s"
                               % {'user_name': user_name, 'reason': e})
            logging.error("%s: Exception received trying to delete user %s"
                          " Exception is: %s",
                          __method__, user_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('User %(user_name)s deleted.'
               % {'user_name': user_name})
        messages.success(request, msg)

        # We are successful -- store away the instance_id onto the session
        # so that we can correctly update our view.
        if hasattr(request, 'session'):
            request.session['instance_id'] = instance_id

        return True


class CreateDatabaseForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"))
    instance = forms.ChoiceField(
        label=_("Instance"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(CreateDatabaseForm, self).__init__(request, *args, **kwargs)

        instID = None

        # If an initial instance id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'instance_id' in kwargs['initial']:
                instID = kwargs['initial']['instance_id']

        # Restrict list of instances to those on which a database can
        # be added (statuses)
        sts = ("ACTIVE",)
        choices = create_instance_choices(request, sts, instID)

        new_list = []
        for choice in choices:
            if choice[0] is None:
                new_list.append((choice[0], choice[1]))
                continue
            instanceID = choice[0]
            instance = retrieve_instance(request, instanceID)
            instance_type = instance.datastore['type']
            if (db_capability.can_create_databases(instance_type)):
                new_list.append((choice[0], choice[1]))

        choices = new_list

        self.fields['instance'].choices = choices

        if instID:
            self.fields['instance'].initial = instID
            self.fields['instance'].widget.attrs['readonly'] = True

    def clean(self):
        instance = self.data['instance']

        if not instance:
            msg = _("Select the instance on which to create the database.")
            self._errors['instance'] = self.error_class([msg])

    def handle(self, request, data):
        __method__ = 'forms.CreateDatabaseForm.handle'

        selected_instance = data['instance']
        database_name = data['name']

        # Need the instance name in both success/failure cases.
        # Retrieve it now (will be instance_id if we couldn't retrieve it).
        instance_name = retrieve_instance(request, selected_instance).name

        # Perform the create database attempt
        try:
            trove_api.trove.database_create(request,
                                            selected_instance,
                                            data['name'],
                                            character_set=None,
                                            collation=None)

        except Exception as e:
            failure_message = ("Attempt to create database %(database_name)s "
                               "on %(instance_name)s was not successful.  "
                               "Details of the error: %(reason)s"
                               % {'database_name': database_name,
                                  'instance_name': instance_name,
                                  'reason': e})
            logging.error("%s: Exception received trying to create "
                          "database %s.  Exception is: %s",
                          __method__, database_name, e)

            redirect = reverse("horizon:dbaas_ui:instances:detail",
                               args=(selected_instance,))
            redirect += "?tab=instance_details__database_tab"
            exceptions.handle(request, failure_message, redirect=redirect)
            return True

        msg = ("Database %(database_name)s created on "
               "instance %(instance_name)s."
               % {'database_name': database_name,
                  'instance_name': instance_name})

        messages.success(request, msg)

        # We are successful -- store away the instance_id onto the session
        # so that we can correctly update our view.
        if hasattr(request, 'session'):
            request.session['instance_id'] = selected_instance

        return True


class DeleteDatabaseForm(forms.SelfHandlingForm):
    database = forms.ChoiceField(
        label=_("Database"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(DeleteDatabaseForm, self).__init__(request, *args, **kwargs)

        selectedDatabase = None

        instance_id = None
        database_name = None

        choices = None

        # If an initial database id was passed in, retrieve it
        # and use it to prime the field
        if 'initial' in kwargs:
            if kwargs['initial'] and 'database_id' in kwargs['initial']:
                selectedDatabase = kwargs['initial']['database_id']
                instance_id, database_name = parse_element_and_value_text(
                    selectedDatabase)
                choices = create_database_choices(request,
                                                  instance_id,
                                                  database_name)
            elif 'data' in kwargs:
                if 'database' in kwargs['data']:
                    selectedDatabase = kwargs['data']['database']
                    instance_id, database_name = parse_element_and_value_text(
                        selectedDatabase)
                    choices = create_database_choices(request,
                                                      instance_id,
                                                      database_name)
                else:
                    choices = create_database_choices(request, None, None)
            else:
                choices = create_database_choices(request, None, None)
        else:
            choices = create_database_choices(request, None, None)

        self.fields['database'].choices = choices

        if selectedDatabase:
            self.fields['database'].initial = selectedDatabase
            self.fields['database'].widget.attrs['readonly'] = True

    def handle(self, request, data):
        __method__ = 'forms.DeleteDatabaseForm.handle'

        instance_id, database_name = parse_element_and_value_text(
            self.data['database'])

        # Perform the delete attempt
        try:
            trove_api.trove.database_delete(request,
                                            instance_id,
                                            database_name)
        except Exception as e:
            failure_message = ("Attempt to delete database %(database_name)s "
                               "was not successful.  Details of the error: "
                               "%(reason)s"
                               % {'database_name': database_name, 'reason': e})
            logging.error("%s: Exception received trying to delete database %s"
                          " Exception is: %s",
                          __method__, database_name, e)
            exceptions.handle(self.request, failure_message)
            # Return true to close the dialog
            return True

        msg = ('Database %(database_name)s deleted.'
               % {'database_name': database_name})
        messages.success(request, msg)

        # We are successful -- store away the instance_id onto the session
        # so that we can correctly update our view.
        if hasattr(request, 'session'):
            request.session['instance_id'] = instance_id

        return True


class ManageRootNoContextForm(forms.SelfHandlingForm):
    # This form is used to prompt the user for a context on which the user
    # wants to manage root access.  The form shows the list of instances and
    # prompts the user to select an instance.  Once an instance is selected,
    # the handle method places the selected instance id on the session where
    # the ManageRootNoContextView can retrieve it (in get_success_url) to
    # open the Manage Root Access panel.
    instance = forms.ChoiceField(
        label=_("Instance"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(ManageRootNoContextForm, self).__init__(request, *args, **kwargs)

        # Restrict list of instances to those on which the root user can be
        # enabled.
        sts = ("ACTIVE",)
        choices = create_instance_choices(request, sts)

        self.fields['instance'].choices = choices

    def clean(self):
        instance = self.data['instance']

        if not instance:
            msg = _("Select an instance on which to manage root access.")
            self._errors['instance'] = self.error_class([msg])

    def handle(self, request, data):
        instance_id = data['instance']

        # Just store away the instance_id onto the session
        # so that we can correctly update our view.
        if hasattr(request, 'session'):
            request.session['instance_id'] = instance_id

        return True


class ManageUserNoContextForm(forms.SelfHandlingForm):
    # This form is used to prompt the user for a context on which the user
    # wants to manage user access.  The form shows the list of instances and
    # users, and prompts the user to select a user/instance.  Once a
    # user/instance combination is selected, the handle method places the
    # selected user/instance id on the session where the
    # ManageUserNoContextView can retrieve it (in get_success_url) to
    # open the Manage User Access panel.
    user = forms.ChoiceField(
        label=_("User"),
        required=True)

    def __init__(self, request, *args, **kwargs):
        super(ManageUserNoContextForm, self).__init__(request, *args, **kwargs)

        # Retireve all users for all instances
        choices = create_user_choices(request, None, None)

        self.fields['user'].choices = choices

    def handle(self, request, data):
        # Retrieve the selected user/instance to manage
        instance_id, user_name = parse_element_and_value_text(
            self.data['user'])

        # Just store away the user and instance_id onto the session
        # so that we can correctly update our view.
        if hasattr(request, 'session'):
            request.session['user'] = user_name
            request.session['instance_id'] = instance_id

        return True
