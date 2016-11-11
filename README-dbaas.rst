=============================
Database as a Service (Trove)
=============================

The Openstack Trove component is installed as part of an OpenStack cluster when
the cluster-genesis project is appropriately configured.  The following
instructions describe the general process::

    git clone git://github.com/open-power-ref-design/cluster-genesis
    cd cluster-genesis
    git checkout release-0.9
    cp domain/configs/dbaas.yml config.yml

At this point, the config.yml file needs to be edited to complete the
configuration. Directions for this are provided in the cluster-genesis project.
When the cluster-genesis project is activated, it will automatically invoke the
bootstrap software that is provided by this project.

General information about the Openstack Trove component can be found at:
https://wiki.openstack.org/wiki/Trove

Installation
------------
The Openstack cluster deployment is done in two parts. An initial bootstrap
script sets up the environment that contain user-configurable parameters that
can be customized, such as passwords and IP addresses. See README.rst for more
details. The following files are installed for Trove:

+-------------------+-----------------------------------------------------------+
| Primary installer | ``/opt/openstack-ansible/playbooks/os-trove-install.yml`` |
+-------------------+-----------------------------------------------------------+
| Ansible role      | ``/etc/ansible/roles/power_trove/``                       |
+-------------------+-----------------------------------------------------------+
| Passwords         | ``/etc/openstack_deploy/user_secrets_trove.yml``          |
+-------------------+-----------------------------------------------------------+
| Container defns   | ``/etc/openstack_deploy/env.d/trove.yml``                 |
+-------------------+-----------------------------------------------------------+

Customization
-------------
After the bootstrap phase, the following parameters can be customized:

* ``/etc/openstack_deploy/user_variables_trove.yml`` (required)

  ``trove_infra_subnet_alloc_start: "172.29.236.100"
  trove_infra_subnet_alloc_end: "172.29.236.110"``

  Trove requires access to the infrastructure network shared by other Openstack
  components. The above variables need to be set to limit the set of IP addresses
  that Trove will use from that network. The addresses must belong to the
  container infrastructure network defined in the inventory file
  ``/etc/openstack_deploy/openstack_user_config.yml``. The definition of that
  network is of the form::

   cidr_networks:
     container: 172.29.236.0/22

  NOTE that the ``openstack_user_config.yml`` file **must** contain a
  ``used-ips`` section that contains the same address range.

* ``/etc/openstack_deploy/user_secrets_trove.yml`` (optional)

  This contains passwords which are generated during the create-cluster phase.
  Any fields that are manually filled in after the bootstrap-cluster phase will
  not be touched by the automatic password generator during the create-cluster
  phase.

Verifying an install
--------------------
After successful installation, verify that Trove services are running correctly.

* Check for existence of Trove container(s) using ``lxc-ls -f`` on the
  controller nodes.

* Attach Trove container using ``lxc-attach -n <container name>``

* Check for existence of 3 Trove processes::

  - trove-api
  - trove-conductor
  - trove-taskmanager

* Source the environment file::

  $ source /root/openrc

* Run some sample trove commands and ensure they run without any errors::

  $ trove list
  $ trove datastore-list
  $ trove flavor-list

Using Trove
-----------
The next step is to build Trove guest images containing database software and
Trove guest agent software, upload them to Glance, and update the Trove
datastore list to map the Glance images to the database versions. Further
details of this process can be found at:
http://docs.openstack.org/developer/trove/#installation-and-deployment

