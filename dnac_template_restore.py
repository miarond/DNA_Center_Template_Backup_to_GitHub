"""
Copyright (c) 2025 Cisco and/or its affiliates.

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
__copyright__ = "Copyright (c) 2025 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

import os
import sys
import time
import json
import glob
import shutil
import time
import pathlib
import logging
from argparse import ArgumentParser

# External packages from PyPi.
import dnacentersdk
from tabulate import tabulate # Only used for printing results to STDOUT - can be re-factored to not use this package.
from git import Repo

# Set up logging
filename=f'dnac_template_restore_{time.asctime()}.log'
handler = logging.FileHandler(filename, "a")
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[handler, logging.StreamHandler()])
logger = logging.getLogger(__name__)

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
github_user = os.getenv('GITHUB_APP_CREDS_USR')
github_password = os.getenv('GITHUB_APP_CREDS_PSW')
dnac_base_url = f'https://{dnac_server}'

# Check if Environment Variables are empty or None.
for var in [dnac_server, dnac_user, dnac_password, github_repo_url, github_user, github_password, dnac_base_url]:
    if var == None or len(str(var)) == 0:
        logger.critical(f'One of the required Environment Variables is empty.')
        sys.exit(1)

# Track counters for final results printout
counters = {
    'dnac_projects': 0,
    'dnac_templates': 0,
    'dnac_projects_created': 0,
    'dnac_projects_failed': 0,
    'templates_imported': 0,
    'templates_failed': 0,
}
# Track all unique template filenames and paths
git_templates = set()

def api_session(args):
    """
    Establish session to DNA Center - update version # if necessary
    params: args (ArgumentParser object)
    returns: api (Global object)
    """
    global api 
    api = dnacentersdk.DNACenterAPI(dnac_user, dnac_password, base_url=dnac_base_url, verify=False, version='2.3.7.6', debug=args.debug_api)


def clone_github_repo(github_repo_url, github_user, github_password):
    """
    Connect to GitHub and clone the given repository.
    params: github_repo_url (str), github_user (str), github_password (str)
    returns: repo (git.Repo() Object)
    """
    global git_templates
    # Insert GitHub credentials into URL
    url_split = github_repo_url.split('//')
    url = f'{url_split[0]}//{github_user}:{github_password}@{url_split[1]}'
    # If directory already exists, remove it.
    if os.path.exists('github'):
        print('Removing existing GitHub repo directory.')
        shutil.rmtree('github')
    repo = Repo.clone_from(url, 'github')
    # Capture all unique filenames and paths of templates in Git repository
    os.chdir(f'{base_working_dir}/github')
    git_templates.update(glob.glob('*/*.json', root_dir=pathlib.Path('projects/')))
    return repo


def build_project_payloads():
    """
    Enumerate all directories in 'projects/' and template files.
    params: None
    returns: payload (JSON object)
    Example: {
        "Project_1": {
            "templates": [
                <template_1_json>,
                <template_2_json>,
                ...
            ]
        },
        ...
    }
    """
    global counters
    projects = {}
    for template in git_templates:
        project_name = template.split('/')[0]
        if projects.get(project_name) != None:
            with open(f'{base_working_dir}/github/projects/{template}', 'r') as f:
                template_content = json.load(f)
            f.close()
            projects[project_name]['templates'].append(template_content[0])
        else:
            projects[project_name] = {'templates': []}
            counters['dnac_projects'] += 1
            with open(f'{base_working_dir}/github/projects/{template}', 'r') as f:
                template_content = json.load(f)
            f.close()
            projects[project_name]['templates'].append(template_content[0])
        counters['dnac_templates'] += 1
    return projects


def create_projects(api, projects):
    """
    Creates projects in DNA Center if they don't already exist.
    params: api (dnacentersdk.DNACenterAPI() Object), projects (JSON object)
    returns: None
    """
    global counters
    existing_projects = api.configuration_templates.get_projects()
    existing = []
    for project in existing_projects:
        existing.append(project['name'])
    for k in projects.keys():
        if k not in existing:
            try:
                response = api.configuration_templates.create_project(name=k)
                logger.info(f'Project import requested for {k}.  Task ID: {response.get("response")["taskId"]}')
                status = check_task_status(api, response.get("response")["taskId"])
                if status:
                    counters['dnac_projects_created'] += 1
                else:
                    counters['dnac_projects_failed'] += 1
            except Exception as e:
                counters['dnac_projects_failed'] += 1
                logger.warning(f'Failed to import project: {k}')
                logger.warning(f'Error: {e}')
        else:
            logger.info(f'Project {k} already exists - skipping.')
    return


def import_templates(api, projects):
    """
    Import templates into DNA Center.
    params: api (dnacentersdk.DNACenterAPI() Object), projects (JSON object)
    returns: None
    """
    global counters
    for k, v in projects.items():
        try:
            response = api.configuration_templates.imports_the_templates_provided(k, do_version=False, active_validation=False, payload=v["templates"])
            logger.info(f'Template import requested for Project {k}.  Task ID: {response.get("response")["taskId"]}')
            status = check_task_status(api, response.get("response")["taskId"])
            if status:
                counters['templates_imported'] += len(v)
            else:
                counters['templates_failed'] += len(v)
        except Exception as e:
            counters['templates_failed'] += len(v)
            logger.warning(f'Failed to import templates for Project: {k}')
            logger.warning(f'Error: {e}')


def check_task_status(api, task_id):
    """
    Check the status of a task.
    params: api (dnacentersdk.DNACenterAPI() Object), task_id (str)
    returns: bool
    """
    try:
        task_status = api.task.get_task_by_id(task_id)
        while task_status.get('response')['endTime'] == None:
            time.sleep(5)
            task_status = api.task.get_task_by_id(task_id)
        logger.info(f'Task ID: {task_id} Status: {task_status.get("response")["progress"]}')
        if task_status.get("response")["isError"]:
            logger.warning(f'Task ID: {task_id} failed. Failure reason: {task_status.get("response")["failureReason"]}')
        return True
    except Exception as e:
        logger.warning(f'Failed to retrieve task status for task ID: {task_id}')
        logger.warning(f'Error: {e}')
        return False


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true', required=False, help='Print verbose output for troubleshooting.')
    parser.add_argument('--debug_api', '-d', action='store_true', required=False, help='Enable debugging output for API session.')
    args = parser.parse_args()

    # Update logging level, if desired
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Open API session to DNAC
    api_session(args)

    # Clone GitHub repository
    repo = clone_github_repo(github_repo_url, github_user, github_password)
    
    projects = build_project_payloads()
    
    # Dump constructed API payloads to output file.
    if args.verbose:
        with open(f"../project_payload_{time.asctime()}.json", "w") as f:
            f.write(json.dumps(projects, indent=4))
            f.close()
    create_projects(api, projects)
    import_templates(api, projects)
    if 'tabulate' in sys.modules:
        logger.info(f'\nResults:\n{tabulate(counters.items(), tablefmt="plain")}')
    else:
        logger.info(f'\nResults:\n{json.dumps(counters, indent=4)}')
