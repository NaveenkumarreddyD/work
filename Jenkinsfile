// MR validation only. No deployment credentials, privileged sockets or deploy network.
pipeline {
  agent { label 'kong-validate' }
  options { timestamps(); timeout(time: 20, unit: 'MINUTES'); disableConcurrentBuilds() }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Secrets') { steps { sh 'bash scripts/security.sh' } }
    stage('Validate all APIs and overlays') { steps { sh 'bash scripts/check.sh' } }
  }
  post { always { archiveArtifacts artifacts: 'evidence/security/*.json', allowEmptyArchive: true } }
}
