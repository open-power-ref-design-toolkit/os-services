#!/bin/bash
#
#
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
#
# Make a patch file given a new file and the original source.
#

if [ $# -ne 4 ]; then
    echo "usage: $0 rel_path orig_file new_file output_dir patch_file"
    echo " "
    echo " rel_path: the relative path to the changed file"
    echo " orig_file: path to the unchange source file"
    echo "   if there is not an existing file pass \"None\" "
    echo " new_file: path to the changed new file"
    echo " patch_file: location to store the patch output"
    echo " "
    echo " This command is only intented to be used by mkdiffs tooling."
    exit 1
fi

# The relative path that we want in the patch file
RELATIVE_PATH=$1
# Any path to the original file
ORIG_FILE=$2
# Any path to the new file
NEW_FILE=$3
# Where to put the patch file
PATCH_FILE=$4
FILE_PATH=$(dirname $ORIG_FILE)

PWD=$(pwd)

echo "Creating patch file for $NEW_FILE"
TMP_DIR=$(mktemp -d /tmp/mkpatch.XXXXXXX)
trap 'rm -rf $TMP_DIR' EXIT

# Create the new file directory and copy the file over to it.
mkdir -p $TMP_DIR/b/$RELATIVE_PATH
cp -a $NEW_FILE $TMP_DIR/b/$RELATIVE_PATH/ >/dev/null

# Create the original file directory and copy the file over to it.
mkdir -p $TMP_DIR/a/$RELATIVE_PATH
# There may not be an original file, check for that condition
if [ "$ORIG_FILE" != "None" ]; then
    cp -a $ORIG_FILE $TMP_DIR/a/$RELATIVE_PATH/ >/dev/null
fi

pushd $TMP_DIR >/dev/null
# Now run the diff
diff -Naur a/ b/ >the_patch_output
rc=$?
popd >/dev/null
if [ $rc -ne 1 ]; then
    echo "diff failed with rc: $rc"
    exit $rc
fi

# Now move the diff output to the target
if [ -e $PATCH_FILE ]; then
    rm $PATCH_FILE
fi
mv $TMP_DIR/the_patch_output $PATCH_FILE

exit 0
