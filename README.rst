os-services
=============

To deploy openstack on a single node or a cluster of nodes pre-configured by genesis::

    >export DEPLOY_CEPH=yes
    >export DEPLOY_OPSMGR=yes
    >export DEPLOY_HARDENING=yes
    >./scripts/bootstrap-cluster.sh
    >./scripts/create-cluster.sh

If the environment variables are omitted or set to "no", then the associated
components are not installed, however if the genesis inventory file exists at
/var/oprc/inventory.yml then DEPLOY_CEPH and DEPLOY_OPSMGR default to "yes".


To deploy openstack on multiple nodes that are not pre-configured by genesis::

    >bootstrap-cluster.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]
    >create-cluster.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]


Debugging hints
---------------

Use the 'screen' command to run the scripts in.  The screen can then be
detached and it will continue running::

    > screen
    > ./scripts/create-cluster.sh 2>&1 | tee /tmp/create-cluster.out

In another terminal you can examine the output or grep for errors::
    > tail -f /tmp/create-cluster.out
    > grep -e "^Failed" -e "^Rebuild" -ie "fatal:" /tmp/create-cluster.out

.. warning::  It is not recommended to use the 'nohup' command.  It is known to
  cause errors while deploying.
