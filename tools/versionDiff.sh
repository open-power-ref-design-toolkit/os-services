#!/bin/bash
# Copyright 2016, 2017 IBM US, Inc.
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


# Create patch/diff files when given 2 versions of source code from git repositories.
# Diff files are created for only those files which are available in both
# ../changes/ and the first git source location.
# For example, dir1 is the first git source location for stable/mitaka 13.1.0 tag and
# dir2 is git source location for stable/mitaka 13.3.5 tag. Then this script traverses
# through the files available in ../changes directory (and subdirectroies recursively)
# and creates diff files for every such file that is found under dir1 (including
# subdirectories of dir1 recursively).
#
# Example usage: ./versionDiff.sh /tmp/.gitsrc_13.1.0 /tmp/.gitsrc_13.3.5
#
# You can use mkdiffs.py to get .gitsrc_13.1.0 and .gitsrc_13.3.5 by running
# mkdiffs.py twice, once with 13.1.0 in mkdiffs.yml and second time with 13.3.5 in
# mkdiffs.yml. When mkdiffs.py is run, the generated .gitsrc directory is located
# at ../.gitsrc
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

#set -x

if [ $# -ne 2 ]; then
    echo "Usage: $0 old_version_gitsrc_loc new_version_gitsrc_loc"
    echo " "
    echo " old_version_gitsrc_loc: Old version's gitsrc location where"
    echo "        source code is already cloned from git repositories"
    echo " new_version_gitsrc_loc: New version's gitsrc location where"
    echo "        source code is already cloned from git repositories"
    exit 1
fi

if [[ ! -d $1 || ! -d $2 ]]; then
    echo "$0 assumes that there are 2 versions of source code located"
    echo "  in the given 2 directories. If not cloned already, please clone"
    echo "  the source code from git repositories and retry $0"
    exit 1
fi

# Old version's git source location where source code is already checked out
# from git repositories
dir1=$1
# New version's git source location where source code is already checked out
# from git repositories
dir2=$2

EXEC_DIR=`dirname $(readlink -f $0)`

# Output dir where the diff files are saved
patch_dir=$EXEC_DIR/../.versionDiffOutput

if [ -d $patch_dir ]; then
    if [ "$(ls -A $patch_dir)" ]; then
        echo -n "$patch_dir is not empty. Are you ok removing $patch_dir?" \
                "Press (y/n):"
        read REPLY
        if [ $REPLY == "y" ]; then
            echo "Removing $patch_dir"
            rm -rf $patch_dir/*
        else
            echo "$patch_dir is not empty. $0 requires empty or nonexisting" \
                 "directory as output directory. Exiting..."
            exit 1
        fi
    fi
else
    mkdir -p $patch_dir
    echo "Output directory where patches will be created:" $patch_dir
fi

# To redirect log messages from this script and mkpatch.sh
log_file=/tmp/versionDiff.log
if [ -f $log_file ]; then
    mv $log_file "$log_file.old"
fi

echo "Input git source locations are:" $dir1 "and" $dir2 >> $log_file 2>&1

# Get the list of files from ../changes directory
files=`cd $EXEC_DIR/../changes;find * -type f`

# Create diff files between 2 versions of source code
for file in $files; do
    rel_path=`dirname $file`
    patch_file=${file//\//-}
    if [ -f  $dir1/$file ]; then
        $EXEC_DIR/mkpatch.sh $rel_path $dir1/$file $dir2/$file \
            $patch_dir/$patch_file.diff >> $log_file 2>&1
    else
        echo "Relative path $file does not exist in gitsrc" \
             $dir1 >> $log_file 2>&1
    fi
done

does_not_exist_cnt=`grep -c 'does not exist in gitsrc' $log_file`
files_unchanged_cnt=`grep -c 'diff failed with rc: 0' $log_file`
modified_files_cnt=`ls -1 $patch_dir|wc -l`
diffs_cnt=`ls -1 $EXEC_DIR/../.diffs|wc -l`
osa_diffs_cnt=`ls -1 $EXEC_DIR/../osa/diffs|wc -l`

echo "Number of files (from changes/) which do not exist in gitsrc" \
     "$dir1:" $does_not_exist_cnt
echo "Number of files which are not modified between the 2 versions:" \
     $files_unchanged_cnt
echo "Number of files which modified between the 2 gitsrc versions:" \
     $modified_files_cnt
echo "Number of files in $EXEC_DIR/../.diffs:" $diffs_cnt
echo "Number of files in $EXEC_DIR/../osa/diffs:" $osa_diffs_cnt

if [ $modified_files_cnt -eq 0 ]; then
    echo "No diff files available in $patch_dir. So no patches to apply" \
         "to $EXEC_DIR/../changes. Exiting..."
    exit 0
fi

echo "Checking if the created patch files from $patch_dir can be applied" \
     "to the files under $EXEC_DIR/../changes"

pushd $EXEC_DIR/../changes > /dev/null 2>&1

num_applicable=0
num_not_applicable=0
num_total_patches=$modified_files_cnt

# Patches that are to be applied in moving from version1 to version2 of OSA
all_patches=()

# Patches which can be applied using patch command without errors
applicable_patches=()

# Patches which result in errors if we try applying them using patch command
non_applicable_patches=()

for file in $files; do
    patch_file=$patch_dir/${file//\//-}.diff
    if [ -f $patch_file ]; then
        all_patches+=($patch_file)
        echo "patch file " $patch_file >> $log_file 2>&1
        patch --dry-run -N -p1 < $patch_file  >> $log_file 2>&1
        rc=$?
        echo "Apply patch dry-run rc="$rc >> $log_file 2>&1
        if [ $rc -eq 0 ]; then
            num_applicable=$((num_applicable+1))
            applicable_patches+=($patch_file)
        else
            num_not_applicable=$((num_not_applicable+1))
            non_applicable_patches+=($patch_file)
        fi
    fi
done

echo $num_applicable "patches out of" $num_total_patches "total patches can" \
     "be applied without issues to $EXEC_DIR/../changes in porting" \
     "os-services code from version $dir1 to version $dir2."

echo "Patches which can be applied without issues are: ${applicable_patches[@]}"

if [ $num_not_applicable -ne 0 ]; then
    echo "You will have to manually resolve the issues and merge" \
         $num_not_applicable "remaining patches."
fi

# Apply the given list of patches
function do_apply_patches {
    patches=("$@")
    #echo "do_apply_patches: ${patches[@]}"

    for patch_file in "${patches[@]}"; do
        if [ -f $patch_file ]; then
            echo "Patch file " $patch_file >> $log_file 2>&1
            # Patches are applied to os-services/changes/ directory
            patch -N -p1 < $patch_file >> $log_file 2>&1
            rc=$?
            echo "Apply patch rc="$rc >> $log_file 2>&1
        fi
    done
}

echo -e "Do you want to proceed with applying patches?"
echo -e "\ta|all to apply all patches to $EXEC_DIR/../changes/ including" \
        "\n\t\tthe patches which do not apply cleanly"
echo -e "\tc|clean_only to apply those patches which can be applied " \
        "\n\t\twithout failures to $EXEC_DIR/../changes/"
echo -e "\tn|none to exit without applying any patches"
echo -ne "  Enter ([a]ll/[c]lean_only/[n]one):"

read -r apply_patches_or_not

case "$apply_patches_or_not" in
    c | clean_only)
        echo "Applying patches which can be applied without failures..."
        do_apply_patches "${applicable_patches[@]}"
        if [ $num_not_applicable -ne 0 ]; then
            echo "You will have to manually resolve the issues and merge" \
                 $num_not_applicable "remaining patches. See $log_file" \
                 "to find the list of patches applied. The patches to be" \
                 "merged manually are: ${non_applicable_patches[@]}"
        fi
        ;;
    a | all)
        echo "Applying all patches including the ones that result in failures"
        do_apply_patches $all_patches
        if [ $non_applicable_patches -ne 0 ]; then
            echo "Patches which resulted in errors are:" \
                 "${non_applicable_patches[@]}"
            echo "You will have to manually resolve the issues and merge" \
                 "these" $num_not_applicable "patches by looking into" \
                 ".rej files mentioned in $log_file"
        fi
        ;;
esac

popd > /dev/null 2>&1

exit 0
