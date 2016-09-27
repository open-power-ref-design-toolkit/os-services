os-services
=============

This project uses the OpenStack Ansible (OSA) project as a base for deploying an
OpenStack cluster on Ubuntu 14.04.  It is assumed the cluster controllers are x86
nodes and the compute nodes are ppc64le.  All nodes are pre-conditioned by the
cluster-genesis project which orchestrates the overall install and configuration
process for the cluster.

To deploy openstack on a cluster of nodes pre-configured by cluster-genesis::

    > export DEPLOY_CEPH=yes
    > export DEPLOY_OPSMGR=yes
    > export DEPLOY_HARDENING=yes
    > export ANSIBLE_HOST_KEY_CHECKING=False
    > export ADMIN_PASSWORD=passw0rd

    > ./scripts/bootstrap-cluster.sh
    > ./scripts/create-cluster.sh

If the DEPLOY_XXX environment variables are omitted or set to "no", then the
associated open source projects are not installed, unless the inventory file
produced by the cluster-genesis project is present at /var/oprc/inventory.yml.
In this case, the variables DEPLOY_CEPH and DEPLOY_OPSMGR default to "yes".

Debugging hints
---------------

The os-services project clones the projects associated with the DEPLOY_XXX environment
variables.  The location of these projects can be externally specified as shown below.

    > export GIT_CEPH_URL=git://github.com/open-power/ceph.git
    > export GIT_OPSMGR_URL=git://github.com/open-power/opsmgr.git

The release tag or branch may be set via the following variables::

    > export CEPH_TAG=master
    > export OPSMGR_TAG=master

The following variable may be used to specify the location of an alternate git mirror::

    > export GIT_MIRROR=github.com

The following variable may be used to install Openstack Tempest for testing purposes::

    > export DEPLOY_TEMPEST=yes

Use the 'screen' command to run the scripts in.  The screen can then be
detached and it will continue running::

    > screen
    > ./scripts/create-cluster.sh 2>&1 | tee /tmp/create-cluster.out

In another terminal you can examine the output or grep for errors::

    > tail -f /tmp/create-cluster.out
    > grep -e "^Failed" -e "^Rebuild" -ie "fatal:" /tmp/create-cluster.out

.. warning::  It is not recommended to use the 'nohup' command.  It is known to
  cause errors while deploying.

Related projects
----------------

    > cluster-genesis
    > ceph
    > opsmgr

For additional information, see::

    >
