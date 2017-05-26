#!/bin/bash
#
# This script can be called by the solutions bootstrap logic by using wget
# to pull it from github, then executing it.
#
# Example:
#   GIT_BRANCH=master
#   URL="https://raw.githubusercontent.com/open-power-ref-design-toolkit/"\
#   "os-services/${GIT_BRANCH}/scripts/bootstrap-solution.sh"
#   wget $URL
#   chmod +x bootstrap-solution.sh
#   ./bootstrap-solution.sh
#
# The solution invoking this script should set all the variables
# needed to properly configure the solution prior to the invocation.
#
# Example:
# export DEPLOY_CEPH=yes
# export DEPLOY_OPSMGR=yes
# export ANSIBLE_HOST_KEY_CHECKING=False
#

OS_SERVICES=${OS_SERVICES:-"https://github.com/open-power-ref-design-toolkit/os-services.git"}

apt-get update >/dev/null 2>&1
type git >/dev/null 2>&1 || apt-get install -qq -y git

if [ ! -d os-services ]; then
    git clone $OS_SERVICES
fi

cd os-services
if [ -n "$GIT_BRANCH" ]; then
    git checkout $GIT_BRANCH
fi

./scripts/bootstrap-cluster.sh | tee -a ../bootstrap-cluster.out
rc=${PIPESTATUS[0]}
if [ $rc != 0 ]; then
    echo "./scripts/bootstrap-cluster.sh failed, rc=$rc"
    exit $rc
fi

HOST=$(hostname -A)
if [ -z "$HOST" ]; then
    HOST=$(hostname)
fi
cat <<EOF

The deployment should now be continued on the first controller node
Please log into "${HOST}" and complete the installation:

ssh ubuntu@${HOST}
sudo su
cd ~/os-services

EOF
