===============
dbimage-builder
===============

The **dbimage-make.sh** command creates a bootable
virtual disk image that is configured to provide
a user specified database from the following list:
**mariadb, mongodb, mysql, postgresql, and redis**.
This list is expected to grow over time, so check back on the
availability of other databases.  Upon successful completion,
this command uploads the image to the OpenStack infrastucture.
It is from these images that running database instances are created.

The images that are produced by **dbimage-make.sh** are
reusable across cloud instances.  The **dbimage-upload.sh**
is provided for this purpose.  Basically, it applies the
same operations that were performed by **dbimage-make-sh**,
after having created the image.  This is a big time savings
and ensures that the exact same bits are re-applied to the new
cloud, excluding the few bits that are updated - ie.
trove-guestagent meta data.

An additional set of commands **dbflavors-show.sh**, **dbflavor-change.sh**,
and **dbflavor-upload.sh** are provided to create database flavors, which
are used to control the size of the database instance.  A
predefined set of these flavors are provided.  The user can
list them, change them at the attribute level (cpu, memory,
storage) and then activate them with the OpenStack
Infrastructure.

These commands are intended to be run when the openstack cluster
is initially deployed, when new database types and versions are
made available, and to introduce or change database flavors.

Scenarios
---------

The following use cases apply for creating database images:

- The distro provides the database.  In this case,
  the user may specify the version of the database (-v)
  to be installed.  This is useful when the distro provides
  more than one version.  If a version is not specified, the
  default version as chosen by the distro is installed.

- The user provides the debian package to be installed.  This
  case applies when the user obtains the package from a vendor
  or community.  It is assumed that the package is self-contained
  in that it is built specifying all prerequisite packages which
  are provided by the distro.  Basically, that the package can
  be installed via a single command invocation.

- The user provides a tar file to be installed.  The tar file must
  contain an install script named setup.sh which is located in the
  root directory of the tar file.

  Tar files are handy in two cases:

  - Vendor provides a debian package, but it has prerequisites
    that are not provided by the distro.  In this case, the
    tar file provides the database and prerequisites.

  - User has a tar file of build artifacts for the named
    database that need to be installed.  Lots of open source
    communities provide tar files as opposed to installable
    distro packages.  The tar file type must be one of tar,
    tgz, or bz2.

This tool internally leverages the OpenStack diskimage-builder project.

dbimage-make.sh
---------------

::

  dbimage-make.sh -d db-name [ -v db-version ] [ -c | -e ] [ -k key-name ]
                             [ -i dib-ip-addr ] [ -p pkg ]

This script creates a bootable O/S image containing the named
database (-d) and database version (-v) and creates an OpenStack Trove
datastore from the image.

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

When a requests results in no supported package, the list of supported
packages is displayed enabling the user to quickly manipulate the
selection criteria to build the desired database image.

Enterprise Editions of databases are usually conveyed with
terms and conditions on use.  It is assumed by this tool that the
user has read those terms and conditions and complies with them
if the user builds a guest database image using the -e argument.

The -k argument names a ssh key pair that is registered with OpenStack.
If this argument is specified, then the public ssh key is obtained from
OpenStack and is placed in virtual disk image in the
file /home/<dib-user>/.ssh/authorized_keys. This is intended for DBA access.

The -i argument identifies a running virtual machine (VM) that should
be used to create the virtual disk image.  This VM must be installed
with Ubuntu 16.04.

The VM associated with the -i argument is created by the user prior
to invoking the dbimage-make.sh script.  This VM may be re-used to
serially create databases images.  If the -i argument is not
specified, then the localhost is assumed.

The -d argument must be one of
mariadb, mongodb, mysql, postgresql, or redis.

The -p argument is a database package that is provided by the user.
This package is installed, instead of a package that is determined by
the tool.  If the -p argument is specified, then the -v argument must
also be specified.

Each invocation of this command
generates one virtual disk image which is automatically uploaded
to OpenStack Glance and associated with a Trove datastore.

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

  dbflavors-show.sh -d db-name

  dbflavors-change.sh -d db-name -f flavor-name
                [ -v vcpus ] [ -m mem-in-gigabytes ]
                [ -c number-of-database-connections-allowed ]
                [ -s root-vdisk1-in-megabytes,db-vdisk2-in-megabytes ]
                [ -b backup-storage-in-megabytes ]

  dbflavors-upload.sh -d db-name -i glance-image-id

The **dbflavors-show.sh** command is typically invoked first to
identify the set of databases that are supported.  A predefined set
of flavors are provided for each database.

The settings associated with each flavor may be changed with the
script **dbflavors-change.sh**.  This script operates on a single
flavor at a time.  The default value of an attribute may be
restored by specifing -1.  If no attribute is specified
( -v, -m, -c. -s, -b), then the default values for given flavor
are restored.

Flavors are uploaded to Trove via the script
**dbflavors-upload.sh**.  The argument related to the
glance id is for the image created with the
script **dbimage-make.sh**.  Once a flavor has been uploaded to
Trove, it should be modified using the OpenStack GUI.

dbimage-upload.sh
-----------------

::

  dbimage-upload.sh -d db-name -v db-version -f <path-to-image>

This command uploads an image previously created by the
**dbimage-make.sh** script.  The image is modified to reflect
the OpenStack cloud associated with the controller that is
named via *dbimagerc* file.

Getting Started
---------------

**dbimage-make.sh** runs in three different execution environments:

- dbimage-make.sh, ansible, and some playbooks run locally under *root*
  where this code is installed.  This node is called the *deployer* node.
  dbimage-make.sh orchestrates the virtual disk image building process.
  Any Ubuntu 16.04 server may provide this orchestration function.
- Some of the playbooks are run on a server in the *OpenStack
  control plane*.  The control plane is referenced to obtain meta data
  that ultimately is placed in the guest image by the dibvm.
- Some of the playbooks are run on a Ubuntu 16.04 *ppc64le* server
  where the image is built.  This node is called the *dibvm*.

The **dbimage-make.sh** command connects to the control plane and the
dibvm over ssh through the *ubuntu* account.  Both servers must provide
*passwordless-sudo* access from the ubuntu account to root.

Considering the above, the tool can be run three different ways:

- It may be run **entirely** within the control plane.  In this
  case, the tool is ready to go as it is automatically installed at
  /root/os-services/osa/dbaas/dbimage-builder on the first
  controller node.  The downside here is that the tool effectively
  creates a development environment in the control plane where
  images are built and accumulated.
- It may be run **partially** from the control plane.  Here, the
  development environment is shifted to another server which must
  be a ppc64le server -- the *dibvm*.  There are a few incidental
  packages installed and an accumulation of images that are
  uploaded to the openstack.  Some may consider the primary downside
  here to be manual access to the root account on an openstack controller.
- It may be run **outside** the control plane from either one
  server or two servers depending on whether the *deployer* and *dibvm* run
  on the same server.  They run under separate user accounts.  However,
  the **dibvm** must be a **ppc64le** server. The advantage of using two servers
  is that the *deployer* may be a *laptop* enabling the user to take the images
  and re-apply them to a different cluster without re-building the image.
  The **dbimage-upload.sh** script is provided for this purpose.  Internally,
  it replaces one file in the image that is specific to the
  OpenStack installation.

The deployer must have at least 1 VCPU and 20 GBs of storage.

The dibvm must have at least 4 VCPUs, 12 GBS RAM, and 100 GBs of storage.

To run outside the control plane, one does::

  git clone git://github.com/open-power-ref-design-toolkit/os-services
  cd os-services/osa/dbaas/dbimage-builder

  edit scripts/dbimagerc
  set 'export DBIMAGE_CONTROLLER_IP=<a.b.c.d>'
  set environment variables to enable ssh connectivity to the controller and dibvm

  ./scripts/dbimage-builder -i <ip-addr-dibvm> -d dbname

  In this scenario, the user is prompted twice for the controller's password.

To run inside the control plane, one does::

  log into the ubuntu account on the first controller.
  sudo su
  cd ~/os-services/osa/dbaas/dbimagerc

  For entirely inside the control plane:

  ./scripts/dbimage-builder -d dbname

  For the external specification of a dibvm:

  set environment variables to enable ssh connectivity to the dibvm
  ./scripts/dbimage-builder -i <ip-addr-dibvm> -d dbname

SSH Setup
---------

This section only applies if the tool is run outside
the control plane.  If it is run from the first OpenStack control
node at */root/os-services/osa/dbaas/dbimage-builder/*
and the **-i** command argument is not
specified, then the tool knows how to connect to local server.
No setup is required.

In general, two ssh connections are established:

1. from the **root** account on the **deployer** to the **ubuntu**
   account on the **controller**
2. from the **root** account on the **deployer** to the **ubuntu**
   account on the **dibvm**

The dbimage-make.sh script sources an environment file that is located
at *dbimage-builder/scripts/dbimagerc*.  This file defines all of the
environment variables that are used by the mechanism.

The controller is identified by setting::

  export DBIMAGE_CONTROLLER=<A.B.C.D>

SSH connectivity may be manually setup by the user prior to running the tool,
or it may be established programmatically by setting the following
environment variables::

  export DBIMAGE_CTRL_PRIVATE_SSH_KEY=<path-to-key>
  export DBIMAGE_CTRL_PASSWD=<password phrase>
  export DBIMAGE_DIB_PRIVATE_SSH_KEY=<path-to-key>
  export DBIMAGE_DIB_PASSWD=<password phrase>

  export DBIMAGE_CTRL_SSH_PROMPT=<yes|no>

The first four environment variables affect the content of the playbook
inventory file which is located at
*dbimage-builder/playbooks/inventory*.  For any given host group,
either the password or the private key may be set to enable
ssh connectivity to the host group.

An alternative approach to access the controller is to be prompted for a
password.  This is enabled by setting the environment variable
DBIMAGE_CTRL_SSH_PROMPT.  One should expect a couple of prompts at the
beginning.

*There is no prompt option provided for the dibvm.*

For the dibvm, ssh connectivity
is required as the dibvm is typically provisioned by the user.

If the user wants to run the dibvm where the tool is installed, then the
**-i** command argument should not be specified.  The user must set
the DBIMAGE_DIB_PRIVATE_SSH_KEY or the DBIMAGE_DIB_PASSWD environment
variable to enable ssh connectivity to the **ubuntu** account on the
local host.

If the tool is invoked from the first OpenStack control node, then
the user does not need to specify either the DBIMAGE_CTRL_PRIVATE_SSH_KEY,
DBIMAGE_CTRL_PASSWD, nor DBIMAGE_ANSIBLE_SSH_PROMPT as the tool
automatically detects the collocation of the deployer and
controller and sets up ssh access.

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
