#!/bin/bash
# Copyright 2016, IBM US, Inc.
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

# Example usage: ./versionDiff.sh /tmp/.gitsrc_13.1.0 /tmp/.gitsrc_13.3.5
#
# You can use mkdiffs.py to get .gitsrc_13.1.0 and .gitsrc_13.3.5 by running
# mkdiffs.py twice, once with 13.1.0 in mkdiffs.yml and second time with 13.3.5 ini
# mkdiffs.yml. When mkdiffs.py is run, the generated .gitsrc directory is located
# at ../.gitsrc

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

#patch_files=`find $patch_dir -type f`
num_applicable=0
total_patches=$modified_files_cnt
for file in $files; do
    patch_file=$patch_dir/${file//\//-}.diff
    if [ -f $patch_file ]; then
        echo "patch file " $patch_file >> $log_file 2>&1
        patch --dry-run -N -p1 < $patch_file  >> $log_file 2>&1
        rc=$?
        echo "Apply patch dry-run rc="$rc >> $log_file 2>&1
        if [ $rc -eq 0 ]; then
            num_applicable=$((num_applicable+1))
        fi
    #else
    #  echo "File path" $patch_file "does not exist. File is not modifed between versions"
    fi
done

echo $num_applicable "patches out of" $total_patches "total patches can" \
     "be applied without issues to $EXEC_DIR/../changes in porting" \
     "os-services code from version $dir1 to version $dir2."

remaining=`expr $total_patches - $num_applicable`
if [ $remaining -ne 0 ]; then
    echo "You will have to manually resolve the issues and merge $remaining" \
         "remaining patches by looking into .rej files."
fi

echo -n "Do you want to proceed with applying all patches to " \
        "$EXEC_DIR/../changes including the patches which do not " \
        "apply cleanly ? Press (y/n):"
read -r apply_or_not

if [ $apply_or_not == "y" ]; then
    for file in $files; do
        patch_file=$patch_dir/${file//\//-}.diff
        if [ -f $patch_file ]; then
            echo "Patch file " $patch_file >> $log_file 2>&1
            # Patches are applied to os-services/changes/ directory
            patch -N -p1 < $patch_file >> $log_file 2>&1
            rc=$?
            echo "Apply patch rc="$rc >> $log_file 2>&1
        fi
    done
    if [ $remaining -ne 0 ]; then
        echo "You will have to manually resolve the issues and merge" \
             $remaining "remaining patches by looking into .rej files" \
             " mentioned in $log_file"
    fi
fi

popd > /dev/null 2>&1

exit 0
