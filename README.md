[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/miarond/DNA_Center_Template_Backup_to_GitHub)

# Template Backup to GitHub with Optional Jenkins Integration

One of the core prerequisites of adopting DevOps practices is to establish a Single Source of Truth.  This is typically a software version control repository of some kind - most often either GitHub or GitLab - and Infrastructure as Code (IaC) definitions are stored in it.  Finally, some form of a Continuous Integration/Continuous Deployment (CI/CD) pipeline is created in order to:

1. Monitor the Source of Truth for changes.
2. Trigger a workflow that runs the changed IaC definition(s) through testing and validation.
3. Upon approval, pushes the changed IaC definition(s) out to the production environment.

As you can imagine, these three simple steps obscure the *great deal* of work required to achieve this outcome.  However, by leveraging product APIs and simple scripting capabilities we can take the first steps toward building a DevOps practice within your organization.

This project contains a Python script which can connect to a Cisco Catalyst Center (formerly DNA Center) appliance *AND* a GitHub repository, download all templates from the Catalyst Center, and compare them (line-by-line) with matching files stored in the GitHub repository.  If there are any updates to existing templates, or if new templates are added, the script will copy those templates into the repository and push them up to the GitHub server.

Additionally, the project contains a Dockerfile definition for creating a Docker image, and a simple Jenkinsfile for building and running the Docker container, which is where the Python script will be executed.  The files in this project provide you with the first step in building a DevOps workflow for maintaining Configuration Templates within your Catalyst Center appliance. (This is a one-way sync - effectively a system for backup and versioning of templates from Catalyst Center to GitHub)

## Getting Started

The Python script relies on four external packages, which must be downloaded and installed from [PyPi.org](https://pypi.org):

* [`dnacentersdk`](https://pypi.org/project/dnacentersdk/): Cisco's Python SDK package for simplifying interactions with Catalyst Center's API interface. 
* [`deepdiff`](https://pypi.org/project/deepdiff/): A Python package for performing deep comparison analysis of JSON datasets.  This is necessary because the order of array elements in the JSON data returned by Catalyst Center's "Export Templates" API (such as the `templateParams` array) is random.  In order to be *certain* that two copies of a template's JSON structure contain identical data, we must compare them element-by-element.
* [`GitPython`](https://pypi.org/project/GitPython/): A Python package that simplifies working with git repositories and communicating with GitHub's APIs.
* [`tabulate`](https://pypi.org/project/tabulate/): A Python package that prints data to STDOUT as nicely formatted tables.
    * OPTIONAL - The Python script can be easily refactored to remove the import statement for tabulate. 

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

Next, take the following steps in GitHub:

1. Ensure that you have created the GitHub repository for storing templates (the same repo assigned to the `GITHUB_DNAC_TEMPLATE_REPO` Environment Variable below).
2. Create an empty folder named `projects` at the root level of this repository.
3. Create a GitHub Personal Access Token under an appropriate account (this account username and PAT are the values assigned to the `GITHUB_APP_CREDS` Environment Variable below), which has permission to `Read` and `Write` to the GitHub repository.

Finally, you will need to create Environment Variables that define your Catalyst Center appliance, username and password, GitHub username and Personal Access Token, and the GitHub repository URL.  The process for creating Environment Variables varies between Windows and Mac/Linux, but you can use the included `default.env` file as a template for creating these variables.  Here is an example for Linux:

```bash
export DNAC_SERVER=192.168.1.1
export DNAC_CREDS_USR=dnacuser
export DNAC_CREDS_PSW=dnacpassword
export GITHUB_APP_CREDS=githubuser:ghp_abcd1234
export GITHUB_DNAC_TEMPLATE_REPO=https://github.com/githubuser/my_repo.git
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

### Running the Python Script in Docker

The included `Dockerfile` can be used to build a Docker Image, using `python:alpine3.18` as the base image.  Alpine Linux is an extremely small and fast OS that can run in a Docker container, using as little as 7MB of space! (or about 52MB when Python3 is installed)  The full image for this project takes up approximately 200MB of space, once all dependencies are installed.  

  > NOTE: Docker requires a Linux operating system to function.  If you are using a Windows or Mac operating system, you will need to install Docker Desktop.

To build a Docker image for this project, run the following command (or similar - you can adjust CLI options as necessary):

```bash
docker build -t dnac_templates .
```

  > The `-t` option applies a "tag", or friendly name, to the resulting image.  The `.` tells Docker to search for a file named `Dockerfile` in the current directory.

Next, you need to ensure the `.env` file has been created and updated with your Environment Variable data, as detailed in the previous section.

  > NOTE: The `Dockerfile` contains a hard-coded `TZ` Environment Variable, for setting the timezone inside the image.  You can update this variable value to change the local timezone inside the image.  This will ensure that log timestamps are adjusted to your desired timezone.

Finally, you can build and run a container based on the new Docker image you just created, and execute the Python script inside it:

```bash
docker run --rm --name dnac_templates --env-file .env dnac_templates python dnac_template_export.py
```

Let's break down this command and explain each component:

* `docker run`: Creates a new container (if the named container doesn't already exist), and runs it.
* `--rm`: Delete the container once it finishes and exits.  If you want to keep the container, you can omit this option.
* `--name dnac_templates`: Assign the friendly name `dnac_templates` to this container.  Yes, it can have the same name as the image used to create it.
* `--env-file .env`: Look for a file named `.env` and use it to generate Environment Variables inside the container.
* `dnac_templates`: The name of the Docker Image to use when creating this container.  We built this image in the first step.
* `python dnac_template_export.py`: The Shell command(s) to pass into the container upon startup.  This will cause the Python script to run inside the container, and upon completion the container will exit and stop.

### Running the Python Script in Docker, on Jenkins

Jenkins is an popular open-source automation server, commonly used by software developers to create CI/CD pipelines, which can build, test and deploy software code.  Jenkins is just one of many tools that can be used to create CI/CD pipelines - I am using it for this project because it is readily available to me.  If you have experience with GitHub Actions, GitLab CI, Circle CI, Travis CI, or many other platforms, you could easily adapt this project to run on them.

This project contains a file named `Jenkinsfile`, which can be used by Jenkins to automatically build and execute a pipeline.  There are many ways to build and execute Jenkins pipelines however, in this example we will leverage GitHub (again) to ***host*** a repository containing all of the code in this project.  The resulting setup works like this:

1. Host this project in a separate GitHub repository.
2. Supply Jenkins with GitHub credentials so that it can clone the repository.
3. Create a new Pipeline project in Jenkins.
4. Define the Pipeline by choosing `Pipeline script from SCM`, and point it at the GitHub repository.
5. Upon executing a "Build", Jenkins will:
    1. Clone the GitHub repository.
    2. Identify the `Jenkinsfile` and begin executing it.
    3. Locate the `Dockerfile` and use it to build a Docker image.
    4. Create a Docker container based on the image, and run it.
    5. Execute the Python script (using Environment Variables defined from "Credentials" objects you create inside Jenkins).
    6. Print the results to STDOUT, stop and remove the container.

There is a lot going on "behind the scenes" here, which Jenkins makes simple for us.  To set up your Jenkins Pipeline, you can follow these steps:

1. Add the credentials and other variable information from the `.env` file to the Credentials Store in Jenkins:
    1. DNA Center Server IP or Hostname:
        1. **Name:** `DNA_Center_Server_IP`
        2. **Type:** `Secret text`
        3. <img src="assets/dna_center_server_ip_credential.png" width=300>
    2. DNA Center Jenkins Credentials:
        1. **Name:** `DNAC_Jenkins_User_Account`
        2. **Type:** `Username with password`
            1. *NOTE: When importing this credential type into a Jenkins Pipeline environment, Jenkins will automatically create ***2*** additional environment variables - one for the username and one for the password.  The username credential will start with the environment variable name, then append `_USR` at the end.  The password credential will append `_PSW` at the end.  Example: `DNAC_CREDS_USR` and `DNAC_CREDS_PSW`.  You can find more information [here](https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#handling-credentials).*
        3. <img src="assets/dna_center_jenkins_credentials.png" width=350>
    3. GitHub API Credentials:
        1. **Name:** `GitHub_Personal_Access_Token`
        2. **Type:** `Username with password`
            1. *NOTE: This credential will be of the same type as the DNA Center credentials listed above, but we will use just the original environment variable name - not the separate `_USR` and `_PSW` variables.  This is because a "Username with password" credential is passed into the original environment variable in the format `username:password`.  This format can be prepended to the beginning of the GitHub API URL to provide authentication.  Example: `https://username:password@github_url.com/repository_path.git`.*
    4. GitHub Template Repository URL:
        1. **Name:** `DNAC_Github_Template_Repo`
        2. **Type:** `Secret text`
            1. *NOTE: This is simply the GitHub repository's URL without the authentication credentials prepended - that step is done within the Python script.  Example: `https://github_url.com/repository_path.git`*
2. Create a new Jenkins Pipeline by clicking the "New Item" button in the left-side menu.  Give the pipeline a name and choose the "Pipeline" project option from the list below:
    1. <img src="assets/create_new_jenkins_pipeline.png" width=300>
3. Configure the Pipeline to obtain its configuration from a separate GitHub repository:
    1. Scroll down to the "Pipeline" section of the configuration page and choose `Pipeline script from SCM` from the "Definition" dropdown menu.
    2. From the "SCM" dropdown menu, choose `Git`.
    3. Enter the "Repository URL" - this is the GitHub repository where the Python script, Dockerfile and Jenkinsfile will be stored.
    4. Choose the appropriate credentials from the "Credentials" dropdown menu.
    5. Edit the "Branch Specifier" field if you are using a branch name *other* than `master`.
    6. Ensure that the "Script Path" field points to the correct location and filename of the `Jenkinsfile` document (if you've renamed or moved it, you will need to specify those changes here).
    7. <img src="assets/jenkins_pipeline_configuration.png" width=400>
4. All other options on the Pipeline configuration page are optional, but some may be useful, such as:
    1. Configuring a Notification Endpoint (like email or an IM space).
    2. A "Build Trigger" for the pipeline - in other words, what will cause this pipeline to run?  You can trigger it manually however, it would be more useful to run the pipeline on a scheduled basis, or to respond to some remote trigger.
        1. *NOTE: A more advanced use-case and potential future project would be to trigger a build based on a GitHub Event Webhook.  It is possible to create a Python script that would update templates in Catalyst Center whenever their JSON files are updated and committed to the template backup repository in GitHub.  Currently this script can not perform that function, but it is possible with some additional work.*
    3. Change the log rotation strategy to clean up old builds.

## Script Workflow

<img src="assets/script_workflow.png" width=600>
