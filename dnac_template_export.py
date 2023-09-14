"""
Copyright (c) 2023 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

__author__ = "Aron Donaldson <ardonald@cisco.com>"
__contributors__ = ""
__copyright__ = "Copyright (c) 2023 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

import os
import sys
import time
import json
import glob
import shutil
import time
from argparse import ArgumentParser

# External packages from PyPi.
from deepdiff import DeepDiff
import dnacentersdk
from tabulate import tabulate # Only used for printing results to STDOUT - can be re-factored to not use this package.
from git import Repo

base_working_dir = os.getcwd()
# The "_USR" and "_PSW" suffixes are automatically created by the Jenkins
# Environment "credentials()" helper method when the credential kind is
# "Username with password"
# If we're working on in a dev environment, use dotenv to load '.env' file
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()
dnac_server = os.getenv('DNAC_SERVER')
dnac_user = os.getenv('DNAC_CREDS_USR')
dnac_password = os.getenv('DNAC_CREDS_PSW')
github_repo_url = os.getenv('GITHUB_DNAC_TEMPLATE_REPO')
github_creds = os.getenv('GITHUB_APP_CREDS')
dnac_base_url = f'https://{dnac_server}'

# Establish session to DNA Center - update version # if necessary
api = dnacentersdk.DNACenterAPI(dnac_user, dnac_password, base_url=dnac_base_url, verify=False, version='2.3.3.0')
# Track counters for final results printout
counters = {
    'dnac_projects': 0,
    'dnac_templates': 0,
    'templates_compared': 0,
    'changed_templates': 0,
    'new_templates': 0,
    'files_updated': 0,
    'file_copy_errors': 0,
    'files_deleted': 0
}
# Track all unique template filenames and paths
dnac_templates = set()
git_templates = set()

def clone_github_repo(github_repo_url, github_creds):
    """
    Connect to GitHub and clone the given repository.
    params: github_repo_url (str), github_creds (str)
    returns: repo (git.Repo() Object)
    """
    global git_templates
    # Insert github_creds into URL
    url_split = github_repo_url.split('//')
    url = f'{url_split[0]}//{github_creds}@{url_split[1]}'
    # Clone or Pull repo to sub-directory named 'github'
    if os.path.exists('github'):
        print('Removing existing GitHub repo directory.')
        shutil.rmtree('github')
    repo = Repo.clone_from(url, 'github')
    # Capture all unique filenames and paths of templates in Git repository
    os.chdir(f'{base_working_dir}/github')
    git_templates.update(glob.glob('projects/*/*.json'))
    os.chdir(base_working_dir)
    return repo


def export_templates(args, api):
    """
    Get a list of all projects, create a folder structure using their names, and then export any new or changed templates into their appropriate folder.
    params: api (dnacentersdk Session Object)
    returns: 
    """
    global counters
    global dnac_templates
    projects = api.configuration_templates.get_projects()
    if args.verbose:
        print(f'Projects:\n{json.dumps(projects, indent=4)}')
    
    if len(projects) > 0:
        # Collect template IDs for next API call
        template_ids = []
        for project in projects:
            counters['dnac_projects'] += 1
            for template in project['templates']:
                # Handle any missing Key instances
                try: 
                    template_ids.append(template['id'])
                except KeyError:
                    pass
        # Request template export for ALL templates (asynchronous task in DNAC)
        template_task = api.configuration_templates.export_templates(payload=template_ids, active_validation=False)
        
        # Check status of task in loop
        loop_counter = 0
        while True and loop_counter < 10:
            export_result = api.task.get_task_by_id(template_task.response.taskId)
            # If key "endTime" is defined, break loop
            if export_result.response.endTime:
                break
            else:
                loop_counter += 1
                time.sleep(0.5)
        if args.verbose:
            print(f'Template export result:\n{json.dumps(export_result, indent=4)}')
        templates = json.loads(export_result.response.data)
        return templates


def deepdiff_files(args, template_export):
    """
    Use the deepdiff package (as needed) to compare contents of GitHub JSON files with DNAC Templates.
    params: args (ArgParse namespace object), template_export (list, contains single template)
    """
    global counters
    global dnac_templates
    
    project = template_export[0]['projectName']
    template = template_export[0]["name"]
    # Add filename and path to dnac global set
    dnac_templates.add(f'projects/{project}/{template}.json')
    git_filename = f'github/projects/{project}/{template}.json'
    # Check if the template exists in the git repo
    result = {}
    if os.path.exists(git_filename):
        with open(git_filename, 'r') as f:
            git_file = json.load(f)
            f.close()
        # Run deepdiff package to compare git file to template export
        result = DeepDiff(template_export, git_file, ignore_order=True)
        counters['templates_compared'] += 1
        # Don't care about 'result' contents, only checking if 'result' 
        # is not empty.
        if len(result) > 0:
            counters['changed_templates'] += 1
    else:
        # If template doesn't exist in git repo, skip deepdiff and add 
        # filename to 'result'
        counters['new_templates'] += 1
        if args.verbose:
            print(f'File {git_filename} does not exist in git repo.')
        result['values_changed'] = {
            'root': {
                'new_value': git_filename
            }
        }
    # Create the new template file in 'projects/' directory if necessary
    if len(result) > 0:
        os.makedirs(f'projects/{project}', exist_ok=True)
        with open(f'projects/{project}/{template}.json', 'w') as file:
            file.write(json.dumps(template_export, indent=4))
        file.close()
    if args.verbose:
        print(f'DeepDiff Result:\n{json.dumps(result, indent=4)}')
    return


def move_changed_files(files):
    """
    Copy files that have changed or are new from the 'projects' directory to the 'github/projects' directory.
    params: files (list)
    """
    global counters
    for file in files:
        # Ensure directory exists first
        try:
            os.makedirs(f'github/{os.path.dirname(file)}', exist_ok=True)
            # Copy file from 'projects/' to 'github/projects/'
            shutil.copy2(f'{file}', f'github/{file}')
            counters['files_updated'] += 1
        except Exception as err:
            print(f'Error copying changed file: {err}')
            counters['file_copy_errors'] += 1


def missing_file_cleanup(args, repo):
    """
    Identify and delete any template files in Git repository that do not currently exist in DNA Center (remove deleted templates).
    params: args (ArgParse namespace object), repo (GitPython Repo object)
    """
    global counters
    # Get differences between filename sets
    deleted_files = git_templates.difference(dnac_templates)
    if args.verbose:
        print(f'Files to be deleted from Git repo:\n{deleted_files}')
    if len(deleted_files) > 0:
        counters['files_deleted'] = len(deleted_files)
        for file in deleted_files:
            repo.index.remove(file, working_tree=True)
    


def git_commit_and_push(repo):
    """
    Commit changes to git repo and push them to GitHub.
    params: repo (git.Repo() Object)
    """
    # Add all untracked files and directories in 'github/projects' to stage
    repo.index.add('projects/*')
    timestamp = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", time.localtime())
    # Commit staged files to index with commit message & timestamp.
    repo.index.commit(message=f'Templates updated by Jenkins Pipeline - {timestamp}')
    # Push commit up to GitHub
    repo.remotes.origin.push()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--compare_only', '-c', action='store_true', required=False, help='Download files and run comparison operation only.')
    parser.add_argument('--verbose', '-v', action='store_true', required=False, help='Print verbose output for troubleshooting.')
    args = parser.parse_args()

    repo = clone_github_repo(github_repo_url, github_creds)
    # If using cached Docker image and 'projects/' dir exists, delete it first.
    # Ran into this problem while testing with Jenkins.
    if os.path.exists('projects'):
        shutil.rmtree('projects')
    os.mkdir('projects')
    templates = export_templates(args, api)
    for template in templates:
        counters['dnac_templates'] += 1
        # API returns templates as Dictionaries but we must enclose them 
        # in a List so JSON files can be reimported into DNAC, if necessary.
        deepdiff_files(args, [template])
    
    if args.verbose:
        print(f'Git repo templates:\n{git_templates}\n')
        print(f'DNA Center templates:\n{dnac_templates}\n')
        print(f'Templates to be deleted:\n{git_templates.difference(dnac_templates)}\n')
    # If 'compare_only' CLI argument was NOT given, proceed.
    if not args.compare_only:
        # If there were any changed or new templates, proceed.
        if counters['changed_templates'] > 0 or counters['new_templates'] > 0:
            os.chdir(base_working_dir)
            # Pass function a list of all JSON files that were created.
            move_changed_files(glob.glob('projects/*/*.json'))
            missing_file_cleanup(args, repo)
            git_commit_and_push(repo)
            # Print URL of GitHub repo ONLY if updates have been pushed.
            print(f'GitHub repository has been updated: {github_repo_url.split(".git")[0]}')
    if 'tabulate' in sys.modules:
        print(f'Results:\n{tabulate(counters.items(), tablefmt="plain")}')
    else:
        print(f'Results:\n{json.dumps(counters, indent=4)}')
