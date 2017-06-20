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

REDIS = "redis"
MONGO = "mongodb"


# Does the datastore allow add/remove/list databases
def can_support_databases(datastore):
    if is_redis_datastore(datastore):
        return False
    else:
        return True


# Does the datastore allow add/remove/list users
def can_support_users(datastore):
    if is_redis_datastore(datastore):
        return False
    else:
        return True


# Does the datastore allow creation of databases
def can_create_databases(datastore):
    if is_redis_datastore(datastore):
        return False
    elif is_mongo_datastore(datastore):
        return False
    else:
        return True


def create_user_requires_database(datastore):
    if is_mongo_datastore(datastore):
        return True
    else:
        return False


def is_mongo_datastore(datastore):
    return (datastore is not None) and (MONGO in datastore.lower())


def is_redis_datastore(datastore):
    return (datastore is not None) and (REDIS in datastore.lower())
