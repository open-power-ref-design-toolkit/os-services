===============
dbimage-builder
===============

The **dbimage-make.sh** command creates a bootable
virtual disk image that is configured to provide
a user specified database.  Upon successful completion,
this command uploads the image to the OpenStack infrastucture.
It is from these images that running database instances are created.
The following databases are currently supported:
**mariadb, mongodb, mysql, postgresql, and redis**.
This list is expected to grow over time, so check back on the
availability of other databases.

The images that are produced by **dbimage-make.sh** are
reusable across cloud instances.  The **dbimage-upload.sh**
is provided for this purpose.  It updates the image so that
it may be integrated into the new cloud instance.  This is
a big time savings as only a few bits need to updated -
ie. ssh keys and trove-guestagent meta data.

An additional set of commands **dbflavor-show.sh**, **dbflavor-change.sh**,
and **dbflavor-upload.sh** are provided to create database flavors which
are used to control the size of the database instance.  A
predefined set of these flavors are provided.  The user can
list them, change them at the attribute level (cpu, memory,
storage) and then activate them with the OpenStack
Infrastructure.

These commands are intended to be run when the OpenStack cluster
is initially deployed, when new database types and versions are
made available, and to introduce or change database flavors.

The commands provided in this toolset are non-privileged, although
*promptless sudo access* is required.  This is required to install
packages. Otherwise, this toolset does not need root access as it
is mostly about creating and managing files produced under the
user's account. The target of this toolset is an OpenStack controller
and operations on it are remotely authenticated via SSH credentials.
In addition, this toolset requires the use of a DIB VM where
OpenStack diskimage-builder project is run to create the image.
The user is responsible for providing the node where this toolset
is run as well as the DIB VM.  In total, there are three nodes
involved - the deployer node which hosts this toolset, the DIB VM,
and an OpenStack Controller node.

The following databases are supported::

  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | Database     | Version  | Source/Edition   | Image Creation  | Notes                                                |
  +==============+==========+==================+=================+======================================================+
  | mariadb      | 10.1     | community        | 25-30 minutes   |                                                      |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | mongodb      | 3.4      | community        | ~2 hours        | Unlink other databases, the OpenDBaaS GUI cannot be  |
  +--------------+----------+------------------+-----------------+ used to create a MongoDB database as MongoDB garbage |
  | mongodb      | 3.4      | enterprise       | 25-30           | collects empty databases.  This means that a mongodb |
  |              |          |                  |                 | client must be used to create and populate the       |
  |              |          |                  |                 | database.  The user associated with this connection  |
  |              |          |                  |                 | must be pre-authorized to create the desired DBs.    |
  |              |          |                  |                 | Use the OpenDBaaS GUI to create the user and specify |
  |              |          |                  |                 | the database(s) to be associated with the account.   |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | mysql        | 5.7      | Ubuntu 16.04     | ~1 hour         |                                                      |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | postgresql   | 9.5      | Ubuntu 16.04     | 25-30           |                                                      |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | postgresql   | 9.6      | community        | 25-30           |                                                      |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | redis        | 3.0      | Ubuntu 16.04     | 25-30           |                                                      |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+
  | redis        | 3.2      | community        | 25-30           |                                                      |
  +--------------+----------+------------------+-----------------+------------------------------------------------------+



dbimage-make.sh
---------------

::

  dbimage-make.sh -d db-name -i dibvm-ip-addr
                [ -v db-version ] [ -c | -e ] [ -k key-name ] [ -I ]

This script creates a bootable O/S image containing the named
database (-d) and database version (-v) and creates an OpenStack Trove
datastore from the image.  The image is built using the
OpenStack diskimage-builder (DIB) project.

The -v argument identifies the version of the database.  Only the
first two components of the version are used.  For example, the user
may specify version 1.2.7.  In this case, the tool would internally
use 1.2 and may even select version 1.2.8 as the distro generally
only provides one version of each package at any given major
minor number where the third component is a fix level.

The -c argument may be specified to select the *community* edition
of a database if one is provided and supported by this tool.
The -e argument may be specified to select the *enterprise* edition
of a database if one is provided and supported by this tool.
When the command arguments -c and -e are not specified, the selection
defaults to a distro provided database if one is provided and
supported by the tool.

The tool internally maintains a lookup table of supported versions
per source of each database.  At least one source is supported per
database and in many cases more than one.
When a request results in no supported package, the list of supported
packages is displayed enabling the user to quickly manipulate the
selection criteria to build the desired database image.

Enterprise editions of databases are usually conveyed with
terms and conditions that the end user is expected to have read,
understood, and accepted.  It is the responsibility of the end
user to find and read these terms and conditions which is
easily done via Google.  For example, search for
'Enterprise edition of MongoDB'.
It is assumed by this tool that the
user has read those terms and conditions and complies with them
if the user builds a guest database image using the -e argument.

The -k argument names a ssh key pair that is registered with OpenStack.
If this argument is specified, then the public ssh key is obtained from
OpenStack and is placed in virtual disk image in the
file /home/<dib-user>/.ssh/authorized_keys. This is intended for DBA access.

The -i argument identifies a running virtual machine (VM)
that should be used to create the virtual disk image.  This VM must be
installed with Ubuntu 16.04 ppc64le.  The DIB tool is installed on this VM.
The VM associated with the -i argument is created by the user prior
to invoking the dbimage-make.sh script.  This VM may be re-used to
serially create databases images.

The -d argument must be one of
mariadb, mongodb, mysql, postgresql, or redis.

The -p argument is a database package that is provided by the user.
This package is installed, instead of a package that is determined by
the tool.  If the -p argument is specified, then the -v argument must
also be specified.  This parameter is not presently implemented.

The -I argument indicates that the qcow2 image should be generated
only.  Don't upload the image to OpenStack Glance or create a Trove
datastore.  This option is usually specified, when the user wants to
customize the image before uploading it via the
**dbimage-upload.sh** command.

Each invocation of the command dbimage-make.sh
generates one virtual disk image which is automatically uploaded
to OpenStack Glance and associated with a Trove datastore (when
the -I option is not specified).

dbflavor commands
-----------------

These commands are used after the datastore has been created
or uploaded by the **dbimage-make.sh** or **dbimage-upload.sh** scripts
respectively.  They are used to create the datastore flavors
which dictate the capacity of datastore instances -- vcpus, ram,
and storage.

The following commands are used to show, change, and upload
database flavors for glance images created
by the script **dbimage-make.sh**::

  dbflavor-show.sh -d db-name [ -p ]

  dbflavor-change.sh -d db-name -f flavor-name
         { [ -c vcpus ] | [ -m mem-in-megabytes ] | [ -r root-vdisk1-in-gigabytes ] }

  dbflavor-upload.sh -d db-name

The **dbflavor-show.sh** command is typically invoked first to
identify the set of databases that are supported.  A predefined set
of flavors are provided for each database.  If the -p argument
is specified, then the default values are specified.  Otherwise
the current values are displayed.

The **dbflavor-change.sh** command changes the settings associated
with a flavor.  At least one setting must be specified.  The default
value for a setting may be restored by specifying -1.

Flavors are uploaded to Trove via the script
**dbflavor-upload.sh**.  Once a flavor has been uploaded to
Trove, it should be modified using the OpenStack GUI/CMDs.

dbimage-upload.sh
-----------------

::

  dbimage-upload.sh -d db-name -v db-version [ -c | -e ] -f qcow-image-name
                  [ -k key-name ] [ -s chroot-cmd ] [ -b dib-user ]

This script creates a Trove datastore from a previously created qcow2 image
which was generated by the script dbimage-make.sh.  Images are located in
the directory os-services/osa/dbaas/dbimage-builder/images/.  If the desired
image is not present in this directory, it can be generated by first running
the script dbimage-make.sh with the -I argument.

The qcow2 image is converted to raw format, mounted, and updated, so that it
will work with the targeted cloud instance.  This involves updating Trove
guestagent meta data, the Trove guestagent stack, and the re-generation of
ssh keys.  The target cloud instance is identified in the dbimagerc file.

In addition, the user may optionally invoke a single user provided command
over the mounted image.  This command is invoked by the chroot command and it
can have no external dependencies on the calling environment as chroot
establishes a new root file system that is strictly based on the
mounted image.  The command cannot reference data in the user's runtime
environment, nor can it be used to copy data into the image.  The command
may be used to invoke commands in the image such as **apt-get, sed, and cat**.

If the user wishes to make several changes to an image, then it is best
to manually update the image and then upload it.  This may
be accomplished in the following way::

    > convert qcow2 image to raw image via the qemu-convert command
      fdisk -l raw-image to identify partitions and offsets
    > calculate the offset of the root partition by multiplying the sector
      size by the starting offset of the partition
    > mount -t ext4 -o loop,offset=<calculated offset> path/to/raw.img /mnt
    > copy or edit files in the mounted image
    > the chroot command may be used to run commands that need to be isolated
      to the mount image.  For example, apt commands should be run via chroot.
      It may be necessary to copy /etc/resolv.conf into the image as this
      file is generated during the initial boot which may not have happened
      yet.
    > when the image is updated as desired, run sync and umount /mnt
    > run dbimage-upload.sh without the -s option

The -d, -v, -k, -c, -e, and -b arguments are the same as for the
**dbimage-make.sh** command.  The -f argument identifies the previously
created qcow2 image that is to be updated.  This image is located in
*dbimage-builder/images/*.  It does not include the path to the image.
For example, -f ubuntu_xenial_mariadb_10_1_c.qcow2.

The -s argument is a command string such as *apt-get -y install x* which
is invoked in a non-interactive shell.

This command uploads an image previously created by the
**dbimage-make.sh** script.  The image is modified to reflect
the OpenStack cloud associated with the controller that is
named via *dbimagerc* file.

Finally, it is important to know the git version of **os-services** project
when the cloud was initially installed as the Trove guestagent code in
the image must be compatible with Trove controller code.  This tool includes
patches which are applied to the guestagent so that newer database versions
can be supported. There are bug fixes as well.  The general rule is that
the same branch of os-services should be used when creating or uploading
images as was initially used to create the cloud. Another option is to
use uplevel tags within the same major version. For example, if the cloud
was installed with os-services version 1.4 (which equals the recipe version),
it is OK to use the upload tool from os-services version 1.5 or 1.6.  It is
not OK to use version 2.0 as that would constitute a change in branch.

Getting Started
---------------

**dbimage-make.sh** runs across three nodes:

- The **Deployer** node where dbimage-make.sh is installed.  This node must be
  installed with Ubuntu 16.04.  *Promptless sudo access* must be provided for the
  user account excluding root that will invoke the toolkit.  If the toolkit
  is invoked as root, then it must be installed under */root/*.  There is no
  processor specific requirement for this node.  dbimage-make.sh provides orchestration
  for image building which occurs on a user provided **DIB VM** and image
  registration with a user specified **OpenStack controller** node, so the
  Deployer node must have network connectivity with these two nodes.  There
  is no requirement that the DIB VM and controller nodes have network connectivity
  with each other.  Both are end-point slaves to the Deployer node.
- The DIB VM is created by the user prior to running the tool.  The deployer
  accesses this node through its *ubuntu* user account which must be pre-configured
  to provide *promptless sudo access*.  This node leverages the OpenStack
  diskimage-builder project to create the image.  This node must be installed
  with Ubuntu 16.04 **ppc64le**.
- The OpenStack controller node is also accessed through its *ubuntu* user account,
  either by SSH keys or password.  The particular method must be pre-configured
  by the user before running the tool.  The password method has the advantage that the
  controller node is not modified.  The disadvantage is that the password is stored
  in plain text on the deployer and may be transmitted that way by Ansible over
  the network.

The deployer must have at least 1 VCPU, 4 GBs RAM, and 20 GBs of storage.  More
storage should be allocated if the user intends to keep all images.  In this case,
80 GBs of storage should be allocated.

The DIB VM must have at least 4 VCPUs, 12 GBs RAM, and 100 GBs of storage.

**Disclaimer**: Running DIB on a VM makes it so it cannot reboot.  If you try
to reboot your VM, or if the cloud has a hiccup and your VM shuts down, it will go
into a grub rescue state and is generally unrecoverable.

The DIB VM is fully managed by the tool. There is no user interaction with it
beyond the initial setup - enabling promptless sudo and SSH connectivity.  If the
VM reaches the error state, it should be destroyed and a new one created.  At most
only the last job is lost and only if it was running at the time of the failure.


SSH Setup
---------

Two ssh connections are utilized:

1. from the <user> account on the **deployer** to the **ubuntu**
   account on the **OpenStack controller**
2. from the <user> account on the **deployer** to the **ubuntu**
   account on the **dibvm**

The dbimage-make.sh script sources an environment file that is located
at *dbimage-builder/scripts/dbimagerc*.  This file defines all of the
environment variables that are used by the mechanism.

The controller is identified by setting::

    export DBIMAGE_CONTROLLER=<A.B.C.D>

SSH connectivity must be manually setup by the user prior to running
the tool.  If the user's default SSH keys, ~/.ssh/id_rsa, are used to
connect to the target node, then no environment variables should need
to be specified to connect to that server.

Set one of following variables to enable alternative forms of SSH connectivity
with the controller via Ansible.  Note the last one instructs Ansible
to prompt the user as it is being run.  If this option is chosen, then
the user is prompted twice at the start of the tool::

    export DBIMAGE_CTRL_PRIVATE_SSH_KEY=<path-to-key>
    export DBIMAGE_CTRL_PASSWD=<password phrase>
    export DBIMAGE_CTRL_SSH_PROMPT=<yes|no>

Set one of the following variables to enable ansible connectivity
with the dibvm::

    export DBIMAGE_DIB_PRIVATE_SSH_KEY=<path-to-key>
    export DBIMAGE_DIB_PASSWD=<password phrase>

There is no prompt option provided for the dibvm.

Some of the environment variables specified above are reflected in
the content of the playbook inventory file which is located at
*dbimage-builder/playbooks/inventory*.  If the credentials for the remote
user changes or a different cloud is targeted, the inventory file
should be removed and dbimagerc should be updated as required.

Deployment
----------

::

    create the deployer VM
    create the dibvm
    ensure ssh connectivity from deployer to controller and dibvm

    enable promptless sudo access

    git clone https://github.com/open-power-ref-design-toolkit/os-services
    cd os-services/osa/dbaas/dbimage-builder

    edit scripts/dbimagerc
    set 'export DBIMAGE_CONTROLLER_IP=<a.b.c.d>' in the file
    optionally set environment variables for alternative ssh connectivity

    scripts/dbimage-make.sh -i <ip-addr-dibvm> -d dbname -k <cloud-key-name>

**Note**: multiple database sources: distro, community, and enterprise are supported,
but not necessarily for every database.  Sources are indicated by -c and -e as well as
by the absence of -c and -e.  It varies per database.  When an invalid source is
specified, an error message indicating the valid sources is displayed.  Look at the
last ~30 lines of output, not just the last line.

Image name customization
------------------------

The **dbimage-make.sh** script creates a virtual guest image.  By default,
the name of this image is composed of the database name (-d), a source component,
and the date of image creation resulting in image names like redis-dib-01-01-2017.  The
source component is intended to identify the tool that was used to create the image
or the owner of the image as Glance allows multiple images with the same name to
be registered.  Each gets a unique Glance ID.  The source component is user
configurable via an environment variable as shown below::

  export DBIMAGE_SOURCE=-dib

Adding custom elements
----------------------

The **dbimage-make.sh** script accepts custom disk image builder elements.
Custom elements can be added to images by setting the DBIMAGE_MYELEMENTS
variable in the scripts/dbimagerc file. The elements must be placed in the
elements directory. The environment variable is a space delimited list of elements.
For example, an element located in ./elements/ubuntu-xenial-hwe-kernel/
is known by the sub-directory in which it is contained - ie. ubuntu-xenial-hwe-kernel.
