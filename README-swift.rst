================================
Object Storage (OpenStack Swift)
================================

The OpenStack Swift component is installed as part of an OpenStack cluster when
the cluster-genesis project is appropriately configured.  The following
instructions describe the general process::

    git clone git://github.com/open-power-ref-design/cluster-genesis
    cd cluster-genesis
    git checkout release-0.9

Select a sample config.yml to use as a starting point for your
configuration, for example::

    domain/configs/swift-large.yml
    domain/configs/swift-medium.yml
    domain/configs/swift-small.yml
    domain/configs/swift-small-with-compute-cloud.yml

Copy the selected file into place::

    cp domain/configs/<filename> config.yml

At this point, the config.yml file needs to be edited to complete the
configuration. General directions for this are provided in the
cluster-genesis project, and Swift specific customization steps
are described below.  When the cluster-genesis project is activated,
it will automatically invoke the bootstrap software that is provided
by this project.

General information about the OpenStack Swift component can be found at:
https://wiki.openstack.org/wiki/Swift

Installation and Customization
------------------------------
Prior to activating cluster-genesis, the following parameters can be customized:

The ``node-templates`` section of config.yml contains a
swift-metadata template for metadata nodes and a swift-object
template for object nodes.  In cases where metadata and object
rings are converged on the same host, only the swift-object
template is present.

Under either swift-metadata or swift-object, the domain-settings
allow devices for each ring to be selected either by pci path or
by individual disk names.  The pci path (e.g. /dev/disk/by-path/pci-0000:01)
will be expanded to include all individual disks on that path.  The
individual disk names (e.g. /dev/sdx) are of course not expanded.

The disk containing the / filesystem will always be avoided.

The account, container, and object device lists cannot partially
overlap.  The lists must either be identical or mutually exclusive.

Here is an example where all rings use the devices on path
pci-0004:03 as well as /dev/sdz.

 .. code-block:: yaml

    node-templates:
        swift-object:
            domain-settings:
                account-ring-devices:
                    - /dev/disk/by-path/pci-0004:03
                    - /dev/sdz
                container-ring-devices:
                    - /dev/disk/by-path/pci-0004:03
                    - /dev/sdz
                object-ring-devices:
                    - /dev/disk/by-path/pci-0004:03
                    - /dev/sdz


The OpenStack cluster deployment is done in two parts. An initial bootstrap
script sets up the environment that contains user-configurable parameters that
can be customized, such as storage policies and passwords. See README.rst
for more details.

After the bootstrap phase, the following parameters can be customized
prior to the create cluster phase:


* ``/etc/openstack_deploy/openstack_user_config.yml`` (optional)

     .. code-block:: yaml

          swift:
            mount_point: /srv/node
            part_power: 8
            storage_network: br-storage
            storage_policies:
            - policy:
                default: 'True'
                index: 0
                name: default


  The default settings (which are shown above) include a 3x replication
  policy for the object ring.  The account and container rings do not
  need to be specified and will use 3x replication.

  The description of each setting that can be changed is shown in
  /etc/openstack_deploy/conf.d/swift.yml.example.

  For example, the default storage policy could be changed to use
  erasure coding:

     .. code-block:: yaml

        storage_policies:
        - policy:
            default: 'True'
            index: 0
            name: default
            policy_type: erasure_coding
            ec_type: jerasure_rs_vand
            ec_num_data_fragments: 10
            ec_num_parity_fragments: 4
            ec_object_segment_size: 1048576


  Here is an example using multiple storage policies, where the default
  storage policy named 'default' uses 3x replication and an additional storage
  policy named 'ec10-4' uses erasure coding:

     .. code-block:: yaml


        storage_policies:
        - policy:
            default: 'True'
            index: 0
            name: default
        - policy:
            index: 1
            name: ec10-4
            policy_type: erasure_coding
            ec_type: jerasure_rs_vand
            ec_num_data_fragments: 10
            ec_num_parity_fragments: 4
            ec_object_segment_size: 1048576

  The swift_hosts section of openstack_user_config.yml shows
  which rings reside on a particular set of drives within each
  host.  This is initially based on the settings provided by
  config.yml prior to the bootstrap phase.  For example:

     .. code-block:: yaml


      swift_hosts:
        swift-object-1:
          container_vars:
            swift_vars:
              drives:
              - groups:
                 - default
                name: disk1
              - groups:
                - default
                name: disk2
              ...

              - groups:
                - default
                name: disk7
              - groups:
                - account
                - container
                name: meta1
              - groups:
                - account
                - container
                name: meta2
              - groups:
                - account
                - container
                name: meta6

* ``/etc/openstack_deploy/user_secrets.yml`` (optional)

  This contains passwords which are generated during the create-cluster phase.
  Any fields that are manually filled in after the bootstrap-cluster phase will
  not be touched by the automatic password generator during the create-cluster
  phase.

Advanced Customization
----------------------
The config.yml file which is used as input to cluster-genesis
allows the devices used by Swift rings to be specified as part of
the ``node-templates`` section.  The cluster-genesis code gathers
inventory information from each node and uses that to populate
a ``nodes`` section of its output inventory file,
/var/oprc/inventory.yml.  For situations where heterogenous hardware
is used, it may be necessary for some hosts to override the devices list
specified in the ``node-templates`` section.

Under normal circumstances, when the cluster-genesis project is activated
it will automatically invoke the bootstrap-cluster.sh that is provided
by the os-services project.  In order to perform the advanced customization
steps described below, you will need to prevent that from happening
so that you have time to modify /var/oprc/inventory.yml.

To customize the disks and devices for the Swift rings on a per-node
basis, modify config.yml to remove the call to boostrap-cluster.sh
before initiating cluster-genesis. After cluster-genesis completes,
modify /var/oprc/inventory.yml on the first controller node as
discussed below and then invoke bootstrap-cluster.sh.

The settings in the node-templates section apply to all nodes in the
corresponding nodes section of /var/oprc/inventory.yml unless an
individual node sets domain-settings to override the template.

Here is an example where node 192.168.16.112 specifies different
devices to override the node-templates section shown above.

    .. code-block:: yaml

        nodes:
            swift-object:
            -   ipv4-pxe: 192.168.16.112
                domain-settings:
                    account-ring-devices:
                        - /dev/sdx
                        - /dev/sdy
                        - /dev/sdz
                    container-ring-devices:
                        - /dev/sdx
                        - /dev/sdy
                        - /dev/sdz
                    object-ring-devices:
                        - /dev/sdx
                        - /dev/sdy
                        - /dev/sdz

Verifying an install
--------------------
After successful installation, verify that Swift services are running correctly.

* Check for the existence of a utility container using ``lxc-ls -f`` on the
  controller nodes.

* Attach the utility container using ``lxc-attach -n <container name>``

* Source the environment file::

  $ source /root/openrc

* Run some sample OpenStack Swift commands and ensure they run
  without any errors::

  $ swift list
  $ swift stat
  $ swift post <containerName>
  $ swift list <containerName>
  $ swift stat <containerName>
  $ swift upload <containerName> <filename>
  $ swift download <containerName> <filename>

* Find the public endpoint URL for the OpenStack Keystone
  identity service, so that it can be used to access Swift
  from remote hosts::

  $ openstack catalog list

Using OpenStack Swift
---------------------
Further information on using the OpenStack Swift client can be found at:
http://docs.openstack.org/user-guide/managing-openstack-object-storage-with-swift-cli.html

Administration for OpenStack Swift
----------------------------------
The OpenStack Ansible playbooks can be used to perform administrative
tasks in the cluster.  The playbooks are found on the deployer node in::

  /opt/openstack-ansible/playbooks

The Swift role for OpenStack Ansible is found in::

  /etc/ansible/roles/os_swift

The settings used by these playbooks are in::

  /etc/openstack_deploy/openstack_user_config.yml

For example, changes to the ring configuration could be made
in openstack_user_config.yml.  Then to refresh Swift services, rebuild
the rings, and push these changes out to the cluster::

  $ cd /opt/openstack-ansible/playbooks
  $ openstack-ansible os-swift-sync.yml --skip-tags swift-key,swift-key-distribute

