#!/usr/bin/env python
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

import argparse
import git
import os
import sys
import yaml


CONF_FILE = 'mkdiffs.yml'
EXEC_DIR, SCRIPT_NAME = os.path.split(sys.argv[0])


def _load_config():
    conf_file = os.path.join(EXEC_DIR, CONF_FILE)
    with open(conf_file, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as ex:
            print(ex)
            raise


def rm_dir(directory):
    if directory != '/':
        os.system('rm -rf ' + directory)
    else:
        print('Tried to remove \'/\' directory')
        exit(1)


def clone_all(conf):
    print ('Cloning the git projects.')
    git_dir = conf['gitsrc_loc']
    for project in conf['changes']:
        print ('  ' + project['git'])
        git_clone(project['git'], project['branch'],
                  git_dir + '/' + project['src_location'])


def confirm_clones(conf):
    git_dir = conf['gitsrc_loc']
    for project in conf['changes']:
        if not os.path.isdir(git_dir + os.sep + project['src_location']):
            print ('Clone not found for project: ' + project['git'])
            exit(1)


def git_clone(url, branch, tgt_dir):
    # Remove the target directory before cloning
    rm_dir(tgt_dir)
    git.Repo.clone_from(url, tgt_dir, branch=branch)


class CreateDiffs(object):

    def __init__(self, conf):
        super(CreateDiffs, self).__init__()
        self.conf = conf
        self.git_dir = conf['gitsrc_loc']
        self.diffs_dir = os.path.normpath(
            os.path.join(EXEC_DIR, self.conf['temp_diff_loc']))
        self.changes_loc = os.path.join(EXEC_DIR, self.conf['changes_loc'])

    def create_dir(self):
        rm_dir(self.diffs_dir)
        os.mkdir(self.diffs_dir, 0755)

    def find_project(self, chgs_loc, chg_path):
        # Remove the changes location and pull out the first directory
        project_name = chg_path.split(chgs_loc)[1].split(os.sep)[1]

        # Now find the project in the conf
        for project in self.conf['changes']:
            if project['src_location'] == project_name:
                return project

        return None

    def create_file_diffs(self):
        norm_chg_loc = os.path.normpath(self.changes_loc)
        for directory, sub_dir, file_names in (os.walk(self.changes_loc)):
            norm_dir = os.path.normpath(directory)
            for file_name in file_names:
                changed_file = os.path.join(norm_dir, file_name)
                print ('Processing: ' + changed_file)

                # Calculate the file relative the changes directory
                relative_change = changed_file.split(norm_chg_loc)[1]
                relative_change = relative_change.lstrip(os.sep)

                # Get the project from the config
                project = self.find_project(norm_chg_loc, norm_dir)

                # Project relative path:
                src_loc = project['src_location']
                prj_rel_path = relative_change[len(src_loc) + 1:
                                               len(relative_change)]

                # Full diff path
                diff_path = (project['target_location'] + os.sep +
                             os.path.dirname(prj_rel_path))

                # Original File
                orig_file_path = (self.git_dir + project['src_location'] +
                                  os.sep + prj_rel_path)
                # Ensure the original file exists.
                if not os.path.isfile(orig_file_path):
                    print ('  Original file not found: ' + orig_file_path)
                    orig_file_path = "None"

                # Diff output file
                diff_file_name = (project['target_location'] + os.sep +
                                  prj_rel_path)
                diff_file_name = diff_file_name.replace(os.sep, '-')
                diff_output_file = (self.diffs_dir + os.sep +
                                    diff_file_name.lstrip('-') + '.patch')

                call_str = ' '.join([os.path.join(EXEC_DIR, 'mkpatch.sh'),
                                    diff_path, orig_file_path,
                                    changed_file, diff_output_file])
                os.system(call_str)


def process_files(skip_git_cloning):
    conf = _load_config()

    if not skip_git_cloning:
        clone_all(conf)
    else:
        confirm_clones(conf)

    crt_diffs = CreateDiffs(conf)
    crt_diffs.create_dir()
    crt_diffs.create_file_diffs()

    print ('\nGenerated patch files are available in directory: %s' %
           os.path.normpath(os.path.join(EXEC_DIR, conf['temp_diff_loc'])))
    print ('The project source is in directory: %s' %
           os.path.normpath(os.path.join(EXEC_DIR, conf['gitsrc_loc'])))


def parse_command():
    """Parse the command arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=("A command to make the patch files. Generated\n"
                     "patch files will be available in the directory\n"
                     "<git top-level directory>/.diffs/."))
    parser.add_argument('-s', '--skip-git-cloning', action='store_true',
                        help='Skip the git cloning.')
    parser.set_defaults(func=process_files)
    return parser


def main():
    parser = parse_command()
    args = parser.parse_args()
    process_files(args.skip_git_cloning)

    print('Done.')

if __name__ == "__main__":
    main()
