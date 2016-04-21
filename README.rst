os-services
=============

This initial drop of code assumes the playbook is running on an ansible
capable system besides the deployer node.  Later, we'll have a script that
will setup the deployer node and it can be run from their directly.  But for
now, run these playbooks remotely (which is easier for development anyway.)


To deploy openstack on a set of nodes:

Ensure the nodes you'll use are setup with a networking configuration that is
compatible with openstack-ansible.

Write your ansible inventory file of the deployer, controller, compute, etc nodes.
The sample inventory sample file can be used then just duplicate and edit.

Run the site yml file

>ansible-playbook -i my_inventory site.yml -kK -u ubuntu

This concludes the remote ansible commands.  The rest of the commands will be
run on the deployer node.

Write your /etc/openstack_deploy/openstack_user_config.yml file.  Your
knowledge of the networking setup of the nodes is key here.  Contruct the file
based off of the samples in the /etc/openstack_deploy directory on the
deployer node.

Set desired passwords in /etc/openstack_deploy/user_secrets.yml

Ensure ssh authorization key for root on the deployer node is set for root
on all other nodes.  Do the setup manually.

Syntax check all the user files:

>cd /opt/openstack-ansible/playbooks
>openstack-ansible setup-infrastructure.yml --syntax-check

Run setup playbook on the deployer node:

>openstack-ansible setup-everything.yml

Go have some coffee, maybe lunch, maybe go dancing.  It'll be back in a while.
