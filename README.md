[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/miarond/DNA_Center_Template_Backup_to_GitHub)

# Template Backup to GitHub Using Python and Ansible

One of the core prerequisites of adopting DevOps practices is to establish a Single Source of Truth.  This is typically a software version control repository of some kind - most often either GitHub or GitLab - and Infrastructure as Code (IaC) definitions are stored in it.  Finally, some form of a Continuous Integration/Continuous Deployment (CI/CD) pipeline is created in order to:

1. Monitor the Source of Truth for changes.
2. Trigger a workflow that runs the changed IaC definition(s) through testing and validation.
3. Upon approval, pushes the changed IaC definition(s) out to the production environment.

As you can imagine, these three simple steps obscure the *great deal* of work required to achieve this outcome.  However, by leveraging product APIs and simple scripting capabilities we can take the first steps toward building a DevOps practice within your organization.

This project contains a Python script which can connect to a Cisco Catalyst Center (formerly DNA Center) appliance *AND* a GitHub repository, download all templates from the Catalyst Center, and compare them (line-by-line) with matching files stored in the GitHub repository.  If there are any updates to existing templates, or if new templates are added, the script will copy those templates into the repository and push them up to the GitHub server.

## Table of Contents

- [Getting Started](#getting-started)
  - [Running the Python Script in Standalone Mode](#running-the-python-script-in-standalone-mode)
    - [CLI Arguments](#cli-arguments)
  - [Running the Script in Ansible Automation Platform](#running-the-script-in-ansible-automation-platform)
    - [Preparing Ansible Automation Platform](#preparing-ansible-automation-platform)
    - [Creating the Project](#creating-the-project)
    - [Creating a Template](#creating-a-template)
  - [Testing Your Automation](#testing-your-automation)
- [Script Workflow](#script-workflow)
- [Restore Templates to Catalyst Center](#restore-templates-to-catalyst-center)

## Getting Started

The Python script relies on four external packages, which must be downloaded and installed from [PyPi.org](https://pypi.org):

* [`catalystcentersdk`](https://pypi.org/project/catalystcentersdk/): Cisco's Python SDK package for simplifying interactions with Catalyst Center's API interface. 
* [`deepdiff`](https://pypi.org/project/deepdiff/): A Python package for performing deep comparison analysis of JSON datasets.  This is necessary because the order of array elements in the JSON data returned by Catalyst Center's "Export Templates" API (such as the `templateParams` array) is random.  In order to be *certain* that two copies of a template's JSON structure contain identical data, we must compare them element-by-element.
* [`GitPython`](https://pypi.org/project/GitPython/): A Python package that simplifies working with git repositories and communicating with GitHub's APIs.
* [`tabulate`](https://pypi.org/project/tabulate/): A Python package that prints data to STDOUT as nicely formatted tables.
    * OPTIONAL - The Python script can be easily refactored to remove the import statement for tabulate. 

Take the following steps in GitHub:

1. Ensure that you have created the GitHub repository for storing templates (the same repo assigned to the `GITHUB_REPO_URL` Environment Variable below).
2. Create an empty folder named `projects` at the root level of this repository.
3. Create a GitHub Personal Access Token under an appropriate account, which has permission to `Read` and `Write` to the GitHub repository.

### Running the Python Script in Standalone Mode

To run the script as a standalone task, you can simply install the required Python packages using the Pip module in Python:

Mac or Linux:
```bash
pip3 install -r requirements.txt
```

Windows:
```
py.exe -m pip install requirements.txt
```

You will need to create Environment Variables that define your Catalyst Center appliance, username and password, GitHub username and Personal Access Token, and the GitHub repository URL.  The process for creating Environment Variables varies between Windows and Mac/Linux, but you can use the included `default.env` file as a template for creating these variables.  Here is an example for Linux:

```bash
export CATC_SERVER=192.168.1.1
export CATC_USERNAME=dnacuser
export CATC_PASSWORD=dnacpassword
export GITHUB_USERNAME=githubuser
export GITHUB_PASSWORD=githubpassword
export GITHUB_REPO_URL=https://github.com/githubuser/my_repo.git
```

Alternatively, you can install the `dotenv` package from PyPi.org (`pip3 install dotenv`), rename the `default.env` file to `.env`, and edit the file accordingly.  If the Python script finds a file named `.env` adjacent to itself, it will attempt to import the `dotenv` package and load the `.env` file values into Environment Variables.

To run the Python script, simply execute it without any command line arguments:

Mac or Linux:
```bash
python3 dnac_template_export.py
```

Windows:
```
py.exe dnac_template_export.py
```

#### CLI Arguments

The Python script accepts two optional command line arguments:

* `--verbose`, `-v`: Print out full details of API responses, and other troubleshooting data.
* `--compare_only`, `-c`: Perform only a comparison of templates between GitHub and Catalyst Center - NO updates or write operations will be performed against the GitHub repository.

For similar help information, you can run the Python script with the `--help` command line argument.

### Running the Script in Ansible Automation Platform

One of the best ways to integrate this automated backup into your network automation solution is to leverage either Ansible (open-source) or RedHat's Ansible Automation Platform (former Ansible Tower).  For the purposes of this documentation, I will detail how to configure Ansible Automation Platform to run this script on a scheduled basis.

#### Preparing Ansible Automation Platform

1. Begin by creating a custom **Credential Type**.  You can do this by choosing the "Credential Types" option under the "Administration" section of the menu, on the left-hand side of the AAP web interface.
2. Click the **Add** button and begin configuring the new Credential Type.  Here are the required configuration options:
    1. `Name`: This is the descriptive name given to the credential type.  Ex.: "Catalyst Center Template Backup Credentials"
    2. `Description`: Optional; you can add additional details here to explain the purpose of the credential type.
    3. `Input configuration` in YAML format (this defines the field names, data types, and whether they are sensitive or required):
    ```yaml
    fields:
      - id: catc_server
        type: string
        label: Catalyst Center Server IP or Hostname
      - id: catc_username
        type: string
        label: Catalyst Center Username
      - id: catc_password
        type: string
        label: Catalyst Center Password
        secret: true
      - id: github_username
        type: string
        label: GitHub Username
      - id: github_password
        type: string
        label: GitHub Password or PAT
        secret: true
      - id: github_repo_url
        type: string
        label: GitHub Template Repository URL
      - id: webex_bot_token
        type: string
        label: Webex Bot Token
        secret: true
    required:
      - catc_server
      - catc_username
      - catc_password
      - github_username
      - github_password
      - github_repo_url
    ```
    4. `Injector configuration` in YAML format (this defines the Environment Variables that will be created in the Execution Environment):
    ```yaml
    env:
      CATC_SERVER: '{{ catc_server }}'
      CATC_PASSWORD: '{{ catc_password }}'
      CATC_USERNAME: '{{ catc_username }}'
      GITHUB_PASSWORD: '{{ github_password }}'
      GITHUB_REPO_URL: '{{ github_repo_url }}'
      GITHUB_USERNAME: '{{ github_username }}'
      WEBEX_BOT_TOKEN: '{{ webex_bot_token }}'
    ```
      > :warning: *Environment Variables are a more secure method of passing sensitive configuration details into an application.  Environment Variables are stored in RAM memory and are only persistent for the current logged in session, which typically safeguards them from accidental disclosure.  **However, be aware that if you set the Logging level of this Playbook to `debug`, it WILL log the contents of all variables to STDERR or STDOUT, which will result in passwords being printed in plain text.***
3. After saving your changes, click on **Credentials** under the "Resources" section of the menu, on the left-hand side of the web UI.  Click the **Add** button to begin creating a new Credential record.
    1. `Name`: The descriptive name of this credential record, identifying what device it pertains to.  Ex: "Catalyst Center 1 - Template Backup Credentials"
    2. `Description`: Optional; you can add additional details here to explain the purpose of the credential record.
    3. `Organization`: Optional but recommended.  By assigning this credential record to a specific Organization in AAP, you can implement role-based access control and limit what users are allowed to use this credential.
    4. `Credential Type`: Select your newly created Credential Type from Step 2.
    5. Fill out all of the fields that appear.
    ![create-new-credential.png](/assets/create-new-credential.png)
    > *Note: The Webex Bot Token field is optional and is used at the end of the Playbook to send the results of the backup job to a Webex Space that you specify.  You can omit this field and remove the Playbook Task that performs this action.*
4. Add an additional Credential record from the same **Credentials** menu page, to specify the GitHub Personal Access Token (PAT) that AAP should use to clone the repository containing this project code.  This **can** be the same PAT that you provided for the custom Credential Type in Step 2 however, the project code should **NOT** be stored in the same repository as the Template backup files.
    > *Note: Ansible Automation Platform does NOT provide an editor interface for Playbooks and automation projects.  This can be confusing at first however, the simple explanation is that AAP relies on an external "Version Control" platform (like GitHub) to store automation projects and provide detailed change control.  Each time an automation task is run in AAP, it creates an Execution Environment (a Docker container), clones the project source code from your version control system (GitHub), and injects any necessary variables and values into the container.*
    1. Follow the same workflow from Step 3 and in the **Credential Type** field, select the **Source Control** type.
    2. Enter your GitHub username in the `Username` field and enter your Personal Access Token (PAT) in the `Password` field.
    ![create-source-control-credential.png](/assets/create-source-control-credential.png)
5. Create an Inventory record for your Catalyst Center server by clicking on the **Inventories** menu option under the "Resources" section.
    1. `Name`: The descriptive name for this inventory group. (A group can contain multiple hosts)
    2. `Description`: Optional; you can add additional details here to explain the purpose of the inventory group.
    3. `Organization`: Allows you to apply role-based access control to this inventory group.
    4. `Tags`: Optional.
6. Create a Host record for your Catalyst Center server by clicking on the **Hosts** menu option under the "Resources" section.
    1. `Name`: The IP address or DNS hostname of this particular host.
    2. `Description`: Optional; you can add additional details here to explain this host.
    3. `Inventory`: Select the Inventory group to assign this host to (created in previous step).
    4. `Variables`: Allows you to add extra variables for this specific host.  For Catalyst Center, and specifically the Python SDK and the Ansible Collection, [additional variables are required](https://github.com/cisco-en-programmability/catalystcenter-ansible/blob/main/README.md#using-environment-variables) for the package to function.
    ```yaml
    ---
    CATALYST_HOST: <A.B.C.D>
    CATALYST_PORT: 443 # optional, defaults to 443
    CATALYST_VERSION: 2.3.7.9 # optional, defaults to 2.3.7.6. See the Compatibility matrix
    CATALYST_VERIFY: False # optional, defaults to True
    CATALYST_DEBUG: False # optional, defaults to False
    ```
    > *Note: Although these variables are required when using the Python SDK or the Ansible Collection directly, in this project we are running a Python script and injecting variable values from the Credential record we created earlier.*

#### Creating the Project

In AAP, a "Project" defines an individual version control repository where the source code of an automation Playbook is stored.  In this example, this repository will be **separate** from the repository used to store backup copies of Catalyst Center's templates.  It will contain the Ansible Playbook, the Python script, the requirements file, and any other necessary files.

1. Click on the **Projects** button under the "Resources" section of the menu, on the left-hand side of the web UI.
2. Click the **Add** button.
3. Fill out the following fields:
    1. `Name`: Descriptive name for the project.
    2. `Description`: Optional; you can add additional details here to explain the purpose of the project.
    3. `Organization`: Allows you to apply role-based access control to this project.
    4. `Execution Environment`: Optional; select the Execution Environment (essentially a Docker image) to use for this project.  If not selected, the default EE will be used.
    5. `Source Control Type`: Select **Git** for the purposes of this project.
    6. `Source Control URL`: The URL of the GitHub repository, used to clone the repository to the local filesystems of AAP.
    7. `Source Control Branch/Tag/Commit`: Optional; allows you to select a branch, tag or commit ID other than the default for this repository.  (Useful for testing code changes contained in an alternative branch).
    8. `Source Control Credential`: Select the GitHub "Source Control" credential record that you created in the previous section.
    9. `Options`: Optional but recommended.  We're selecting **Clean** (remove any local changes) and **Update Revision on Launch** (sync the repository from source control before each launch).
    10. `Cache Timeout`: The number of minutes to store and use the local copy of the repository, before having to resync from source control.
    ![create-new-project.png](/assets/create-new-project.png)
4. Click the **Save** button.
5. Wait for the initial sync (clone) of the repository to complete and display a **Successful** status.  If the status is **Failed**, this indicates that a problem occurred and you will need to inspect the logs to determine the cause.

#### Creating a Template

In AAP, Templates define a specific automation workflow that leverages the source code contained in the Project that we created in the previous section.  The Project source code is modular enough to support any number of Catalyst Center installations - a Template defines what specific Catalyst Center to leverage the source code for, in order to back up a copy of its templates.  It ties the Playbook to Inventory groups.

1. Click on the **Templates** button under the "Resources" section of the menu, on the left-hand side of the web UI.
2. Click the **Add** button.
3. Fill out the following fields:
    1. `Name`: Descriptive name for the template.
    2. `Description`: Optional; you can add additional details here to explain the purpose of the template.
    3. `Job Type`: Select whether to run the template or simply check the validity of the Playbook, plus the variables.  We will always use **Run**.
    4. `Inventory`: Select the Inventory group that you created in the first section.
    5. `Project`: Select the Project that you created in the previous section.
    6. `Execution Environment`: Optional; select the Execution Environment (essentially a Docker image) to use for this template.  If not selected, the default EE will be used.
    7. `Playbook`: This field is dynamically populated with all `.yml` or `.yaml` Playbook files that have been located in the source code of the Project you selected.  Choose the `backup_templates_to_github.yml` Playbook file.
    8. `Credentials`: Select the custom credential type that you created in the first section, and then select the specific credential record you created.
    9. `Variables`: Add any extra variables you would like to inject into the Playbook.  In our example, we're specifying the Webex Chat Space that we want our Webex Bot to send status messages to, using the variable name `webex_room_id`.
    10. `Verbosity`: Select **0 (Normal)** for most cases.  If you are testing/troubleshooting a new Playbook, you can select a higher level of logging, such as **3 (Debug)**.
    > :warning: ***If you choose "Debug" level of verbosity, this project WILL print out passwords from your credentials record in PLAIN TEXT to the STDOUT or STDERR output log.***
4. Click the **Save** button.

### Testing Your Automation

Once you have completed the setup steps listed above, you can now attempt to run your **Template** and evaluate whether it works, or review the output logs if it doesn't.

1. Click on the **Templates** button under the "Resources" section of the menu, on the left-hand side of the web UI.
2. Click on the name of the template you created in the previous section.
3. Click the **Launch** button.
4. Follow the Playbook output logs from the **Output** tab.  
    > *Note: You will likely be prompted to click on the **Reload output** link at the top of the output window, once the template job is complete.*
5. Playbook output is often truncated in AAP's web UI however, you can expand the truncated sections to view the full output.  Look for line numbers that are missing, along with an ellipsis (...) showing up in the output:
    1. ![template-job-output.png](/assets/template-job-output.png)
    2. Click on the ellipsis and a pop-up window will open.
    3. Click on the either the **JSON** or **Output** tabs to view the full log output.
    ![full-log-output.png](/assets/full-log-output.png)

## Script Workflow

<img src="assets/script_workflow.png" width=600>

## Restore Templates to Catalyst Center

The Python script named `dnac_template_restore.py` has been added to simplify and automate the task of restoring backed up templates to a Catalyst Center appliance, in the event of disaster recovery or other loss of data.  **PLEASE NOTE:** Backward compatibility between older versions of exported template files and newer versions of Catalyst Center software is not guaranteed, and will often fail during import due to changes in the payload structure.  In these situations you will need to either edit the JSON file to fix any incompatibilities, or simply recreate the template manually.

This script will download a copy of your GitHub repository (created by using the `dnac_template_export.py` script) and recursively search the directory structure.  It will create any Projects that do not already exist and will attempt to import all Templates belonging to each Project.  In its current form, the script imports all Project templates in a single bulk task, so if one or more of the templates already exists it will attempt to create commit a new version.  If an error is encountered, it is possible that ALL templates included in the Project may fail to import - even if only one templates contains an error.
This script will download a copy of your GitHub repository (created by using the `dnac_template_export.py` script) and recursively search the directory structure.  It will create any Projects that do not already exist and will attempt to import all Templates belonging to each Project.  In its current form, the script imports all Project templates in a single bulk task, so if one or more of the templates already exists it will attempt to commit a new version.  If an error is encountered, it is possible that ALL templates included in the Project may fail to import - even if only one templates contains an error.

To use this script, ensure that your `.env` file has been updated with accurate information, then run the script:

```
python3 dnac_template_restore.py
```

The script accepts two optional arguments:

- `-v` or `--verbose`
    - Enable Debug level logging to both the terminal and the log file
- `-d` or `--debug_api`
    - Enable Debug level logging in the `dnacentersdk` Python package.  **This will significantly increase logging output.**

Logging is output to both the terminal and a log file named `dnac_template_restore_<current date/time>.log`.  When Verbose logging is enabled, the generated template payloads for the template import API are exported to a JSON file named `project_payload_<current date/time>.json`.