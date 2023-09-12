pipeline {
  environment {
    DNAC_SERVER = credentials('DNA_Center_Server_IP')
    DNAC_CREDS = credentials('DNAC_Jenkins_User_Account')
    GITHUB_APP_CREDS = credentials('GitHub_Personal_Access_Token')
    GITHUB_DNAC_TEMPLATE_REPO = credentials('DNAC_Github_Template_Repo')
  }
  agent any
  stages {
    stage('Build Image') {
      agent { 
        dockerfile true
      }
      steps {
        script {
          output = sh(returnStdout: true, script: 'python dnac_template_export.py').trim()
          println "${output}"
        }
      }
    }
  }
}