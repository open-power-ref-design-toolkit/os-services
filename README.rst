os-services
===========

This project uses the OpenStack Ansible (OSA) project as a base for deploying an
OpenStack cluster on Ubuntu 16.04. All nodes are pre-conditioned by the
cluster-genesis project which orchestrates the overall install and configuration
process for the cluster.

To deploy OpenStack on a cluster of nodes pre-configured by cluster-genesis::

    > export DEPLOY_CEPH=yes
    > export DEPLOY_OPSMGR=yes
    > export DEPLOY_HARDENING=yes
    > export ANSIBLE_HOST_KEY_CHECKING=False
    > export ADMIN_PASSWORD=passw0rd

    > ./scripts/bootstrap-cluster.sh
    > Manual configuration of OpenStack-Ansible parameters
    > ./scripts/create-cluster.sh

If the DEPLOY_XXX environment variables are omitted or set to "no", then the
associated open source projects are not installed, unless the inventory file
produced by the cluster-genesis project is present at /var/oprc/inventory.yml.
In this case, the variables DEPLOY_CEPH and DEPLOY_OPSMGR default to "yes".

Manual configuration of OpenStack-Ansible parameters
----------------------------------------------------

Manual configuration is required to integrate the cloud that is being created
into your data center. The following list represents some of the items that
need to be configured. Consult your OpenStack-Ansible documentation for a
complete list of parameters that need to be set::

    > Configure SSL Certificates
    > Reserve a set of IP Addresses that OpenStack should not allocate
    > Allocate IP Address Range for expansion of controller, storage, and compute nodes
    > Allocate a set of IP Addresses for OpenStack Trove to use
    > Setting a unique VRRP ID for keepalived for network high availability

Be sure to consult with your data center administrator for site specific
policies regarding the use of SSL Certificates and floating external IP
addresses as well as the selection of a unique VRRP ID within the data
center. There is a lot of documentation related to OpenStack networking
(Neutron) that is available on the internet. The following topics
may be searched online to find more information::

    > Legacy networking with Linux bridges
    > High Availability using VRRP (L3HA) with Linux bridges
    > Provider networks with Linux bridges

Debugging hints
---------------

The os-services project clones the projects associated with the DEPLOY_XXX environment
variables. The location of these projects can be externally specified as shown below::

    > export GIT_CEPH_URL=git://github.com/open-power-ref-design-toolkit/ceph-services.git
    > export GIT_OPSMGR_URL=git://github.com/open-power-ref-design-toolkit/opsmgr.git

The release tag or branch may be set via the following variables::

    > export CEPH_TAG=master
    > export OPSMGR_TAG=master

The following variable may be used to specify the location of an alternate git mirror::

    > export GIT_MIRROR=github.com

The following variable may be used to install OpenStack Tempest for testing purposes::

    > export DEPLOY_TEMPEST=yes

Use the 'screen' command to run the scripts in. The screen can then be
detached and it will continue running::

    > screen
    > ./scripts/create-cluster.sh 2>&1 | tee /tmp/create-cluster.out

In another terminal you can examine the output or grep for errors::

    > tail -f /tmp/create-cluster.out
    > grep -e "^Failed" -e "^Rebuild" -ie "fatal:" /tmp/create-cluster.out

.. warning::  It is not recommended to use the 'nohup' command.  It is known to
  cause errors while deploying.

Bug Reporting
-------------
The current list of bugs can be found on launchpad:
https://bugs.launchpad.net/open-power-ref-design

Related projects
----------------

OpenStack based recipes for OpenPOWER servers are located here:

    - `openstack-recipes <https://github.com/open-power-ref-design/>`_

Here, you will find information about:

    - `Private cloud w/ and w/o Swift Object Storage <https://github.com/open-power-ref-design/private-compute-cloud/blob/master/README.rst>`_
    - `Database as a Service (OpenStack Trove) <https://github.com/open-power-ref-design/dbaas/blob/master/README-dbaas.rst>`_
    - `Standalone Swift Clusters (OpenStack Swift) <https://github.com/open-power-ref-design/standalone-swift/blob/master/README-swift.rst>`_
    - `Standalone Ceph Clusters <https://github.com/open-power-ref-design/standalone-ceph/blob/master/README-swift.rst>`_

The following projects provides services that are used as major building blocks in
recipes:

    - `cluster-genesis <https://github.com/open-power-ref-design-toolkit/cluster-genesis>`_
    - `ceph-services <https://github.com/open-power-ref-design-toolkit/ceph-services>`_
    - `opsmgr <https://github.com/open-power-ref-design-toolkit/opsmgr>`_
