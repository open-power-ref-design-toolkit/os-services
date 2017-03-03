#!/bin/bash
# Copyright 2017 IBM US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Script that compares patch files with same names in 2 directories and shows
# the diff of patch files for which the file contents are not same. The diff
# from all the files is saved in the log file. This script doesn't show
# any diff if a file is there in only one of those two directories. This
# script ignores the diff of lines (that start with "--- a/" or "+++ b/") which
# contain the file paths and date and timestamps. After running this script,
# go through the log file /tmp/cmpDiffs.log and manually update remaining
# files in porting os-services to a new OSA version.
#
#
# Usual steps in porting os-services to a new OSA version:
# (1) Run mkdiffs.py to get old OSA version git source code and then save it.
#       ./mkdiffs
#       cp -R ../.gitsrc ~/gitsrc_v1
# (2) Modify the version/tag of different(all) roles in mkdiffs.yml to the
#     new version from old version. Run mkdiffs.py again to get the new
#     version's .gitsrc and save that also.
#       ./mkdiffs
#       cp -R ../.gitsrc ~/gitsrc_v2
# (3) Run versionDiff.sh to get the differences between gitsrc_v1 and
#     gitsrc_v2 for the files under ../changes/
#       ./versionDiff.sh ~/gitsrc_v1 ~/gitsrc_v2
#     Choose c[to apply cleanly applicable patches only] or a[to apply all
#     patches; some of these will result in .rej files, which require
#     manual attention/merge]
# (4) Once all the code changes to ../changes/ are done, run mkdiffs.py to get
#     the patch files in ../.diffs directory. Copy the required .patch files
#     from ../.diffs/ to ../osa/diffs/
#     Refer to the next point (5) that helps in deciding which patch files are
#     to be copied from ../.diffs/ to ../osa/diffs/ and also in copying
#     automatically.
# (5) Once the porting is completed (including manually merging all the
#     patches from ../.versionDiffOutput/ to ../changes), run cmpDiffs.sh
#     which helps in copying the patch files from ../.diffs to ../osa/diffs
#     after prompting for y/n for copying:
#       ./cmpDiffs.sh ../.diffs ../osa/diffs
#     If there are differences shown in the log file /tmp/cmpDiffs.log and
#     if we choose option y in y/n for copying patch files from ../.diffs to
#     ../osa/diffs, then rerun cmpDiffs.sh to validate that there are no
#     more differences between the patches from ../.diffs and ../osa/diffs.
#     The resultant log file /tmp/cmpDiffs.log should not contain any
#     differences. The following command should give empty output if porting
#     of os-services to new version is complete:
#     grep -v -e 'FILE:' -e 'No differences between' /tmp/cmpDiffs.log
# (6) Make any other related changes like the release name change in the line
#     that has "git checkout" and the value of OSA_TAG variable in
#     ../osa/scripts/bootstrap-osa.sh
# (7) You may have to remove patches from ../osa/diffs/ if the corresponding
#     source file is removed from a subdirectory under os-services/changes/ as
#     part of porting os-services from one version of OSA to another.


if [ $# -ne 2 ]; then
    echo "Usage: $0 dir1 dir2"
    echo " "
    echo " dir1: The directory under which patch files are traversed and"
    echo "        the contents of the patch files under this directory are"
    echo "        compared against files under dir2"
    echo " dir2: The directory under which files with the same names as"
    echo "        those of files under dir1 and then contents of files"
    echo "        are compared"
    exit 1
fi

if [[ ! -d $1 || ! -d $2 ]]; then
    echo "$0 assumes that there are 2 directories given as input. The files"
    echo "  under these 2 directories are compared. Make sure that the"
    echo "  directories exist and retry $0"
    exit 1
fi


dir1=$1
dir2=$2

# Assume .patch in file names
files=`find $dir1 -type f -name '*.patch'`

# To redirect log messages from this script
log_file=/tmp/cmpDiffs.log
if [ -f $log_file ]; then
    mv $log_file "$log_file.old"
fi

# Ignore lines with these patterns because they are the lines with just
# file paths and date and timestamps
p1='^--- a/'
p2='^+++ b/'

num_patches_to_be_copied=0
num_failures=0
for file in $files; do
    file_name=`basename $file`
    echo "FILE: $file" >> $log_file

    if [ -f $dir2/$file_name ]; then
        diff <(grep -v -e "$p1" -e "$p2" $file) \
             <(grep -v -e "$p1" -e "$p2" $dir2/$file_name) >> $log_file
        rc=$?
        if [ $rc -eq 0 ]; then
            echo "No differences between" $file "and" \
                 $dir2/$file_name >> $log_file
        elif [ $rc -eq 1 ]; then
            echo "Differences exist between the files" $file "and" \
                 $dir2/$file_name >> $log_file
            num_patches_to_be_copied=$((num_patches_to_be_copied+1))
        else
            echo "diff command returned error when comparing files" \
                 $file "and" $dir2/$file_name >> $log_file
            num_failures=$((num_failures+1))
        fi
    else
        echo $file_name "does not exist in" $dir2 >> $log_file
    fi
done

echo "See $log_file for details of diff of patch files between directories" \
     $dir1 "and" $dir2
if [ $num_patches_to_be_copied -eq 0 ] && [ $num_failures -eq 0 ]; then
    echo "It seems there are no patch files to be copied to" $dir2 \
         ". Porting os-services may be complete except probably changing" \
         "the OSA_TAG in bootstrap-osa.sh"
fi

cat <<MSG
Do you want to copy the patch files from ../.diffs directory which are different
from the patch files available in ../osa/diffs directory ? Enter (y/n):
MSG

read REPLY
if [ $REPLY == "y" ]; then
    # Create /tmp/copyDiffs.sh and run it to copy the patch files from
    # ../.diffs/ to ../osa/diffs/
    echo "Copying patch files from" $dir1 "to" $dir2
    echo '#!/bin/bash' > /tmp/copyDiffs.sh
    grep 'Differences exist between the files' /tmp/cmpDiffs.log >> /tmp/copyDiffs.sh
    sed -i 's/^Differences exist between the files/cp/; s/ and / /' /tmp/copyDiffs.sh
    # Also copy patch files which are there in dir1 but not there in dir2
    grep 'does not exist in' /tmp/cmpDiffs.log | sed "s/does not exist in//; s[^[cp $dir1/[" >>/tmp/copyDiffs.sh
    /bin/bash /tmp/copyDiffs.sh
fi

if [ $num_failures -ne 0 ]; then
    echo "There are" $num_failures "failures when trying diff between" $dir1 \
         "and" $dir2 ". See $log_file for more details."
fi

exit 0
