os-services
=============

To deploy openstack on a single node or a cluster of nodes pre-configured by genesis::

    >export DEPLOY_CEPH=yes
    >export DEPLOY_OPSMGR=yes
    >export DEPLOY_HARDENING=yes
    >nohup ./scripts/bootstrap-cluster.sh &
    >nohup ./scripts/create-cluster.sh &

If the environment variables are omitted or set to "no", then the associated
components are not installed.


To deploy openstack on multiple nodes that are not pre-configured by genesis::

    >bootstrap-cluster.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]
    >create-cluster.sh [ -i <controllernode1,...> -s <storagenode1,...> -c <computenode1,...> ]


Debugging hints::

    > Use nohup to generate a log file.  You can logout and it will continue running

    > nohup ./scripts/create-cluster.sh &
    > tail -f nohup.out

    > grep -e "^Failed" -e "^Rebuild" -e "^ValueError" nohup.out
