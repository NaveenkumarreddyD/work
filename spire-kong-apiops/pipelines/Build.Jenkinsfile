// Standalone trusted job Kong/Build. Jenkinsfile SCM must be ADMIN-PINNED tooling.
// Trigger on protected-main push (webhook) and poll main as a fallback; never from MR jobs.
properties([parameters([string(name:'RELEASE_TAG',defaultValue:'',description:'Empty = current protected main and automatic DEV. Otherwise existing protected signed tag.')]),
  pipelineTriggers([pollSCM('H/5 * * * *')]), disableConcurrentBuilds(), buildDiscarder(logRotator(numToKeepStr:'100'))])
if (params.RELEASE_TAG && !(params.RELEASE_TAG ==~ /kong-v\d+\.\d+\.\d+(-rc\d+)?/)) error('Invalid release tag')
def cfg
def apiNames=[]
def enabledDev=[]
def ref
node('kong-release') {
  timeout(time:40,unit:'MINUTES') {
    deleteDir()
    checkout scm
    cfg=readJSON(file:'pipelines/settings.json')
    if (!cfg.repository_url || !cfg.scm_credentials_id) error('Configure trusted source repository and read-only SCM credential first')
    // Save trusted helper outside candidate checkout. No code from the tag runs until identity passes.
    def verifySource=readFile('scripts/verify-source.sh')
    dir('candidate') {
      checkout([$class:'GitSCM',branches:[[name:'*/main']],userRemoteConfigs:[[url:cfg.repository_url,credentialsId:cfg.scm_credentials_id]],extensions:[[$class:'CloneOption',noTags:false,shallow:false]]])
      writeFile(file:'.git/verify-source.sh',text:verifySource)
      withEnv(["RELEASE_TAG=${params.RELEASE_TAG}","REQUIRE_SIGNED_TAG=${cfg.require_signed_tags}"]) {
        if (params.RELEASE_TAG) {
          def commit=sh(script:'bash .git/verify-source.sh "$RELEASE_TAG"',returnStdout:true).trim()
          if (!(commit ==~ /[a-f0-9]{40}/)) error('Invalid source commit')
          withEnv(["VERIFIED_COMMIT=${commit}"]) { sh 'git checkout --detach "$VERIFIED_COMMIT"' }
          ref=params.RELEASE_TAG
        } else {
          def commit=sh(script:'git rev-parse HEAD',returnStdout:true).trim()
          ref="dev-${commit}"
        }
        stage('Validate reviewed source without deployment credentials') {
          sh 'bash scripts/security.sh && bash scripts/check.sh'
        }
        apiNames=findFiles(glob:'apis/*/metadata.yaml').collect { it.path.tokenize('/')[1] }
        if (!apiNames) error('No APIs found')
        for (api in apiNames) {
          if (!(api ==~ /[a-z][a-z0-9-]{2,62}/)) error('Invalid API directory')
          withEnv(["REF=${ref}","API=${api}"]) {
            sh 'bash scripts/release.sh "$REF" "$API" "releases/$REF/$API"'
            def m=readJSON(file:"releases/${ref}/${api}/manifest.json")
            if (m.environments.dev.enabled) enabledDev.add(api)
          }
        }
      }
      // Retain identical environment-specific bytes for every promotion. Artifact paths are data only.
      archiveArtifacts artifacts:'releases/**',fingerprint:true
    }
  }
}
// Finish building every package before starting any live change.
if (!params.RELEASE_TAG) {
  for (api in enabledDev) {
    build job:cfg.jobs.dev,wait:true,propagate:true,parameters:[string(name:'PACKAGE_BUILD',value:env.BUILD_NUMBER),string(name:'REF',value:ref),string(name:'API',value:api),string(name:'ACTION',value:'DEPLOY')]
  }
}
