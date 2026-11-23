// Install one protected standalone job per environment. This script is ADMIN-PINNED tooling.
// Set job-level TARGET_ENV to a fixed environment. Users cannot choose credential scope.
properties([parameters([
  choice(name:'ACTION',choices:['DEPLOY','ROLLBACK']),
  string(name:'PACKAGE_BUILD',defaultValue:'',description:'Retained Kong/Build number'),
  string(name:'REF',defaultValue:'',description:'Protected kong-vX.Y.Z tag; DEV also accepts dev-<40-char-commit>'),
  string(name:'API',defaultValue:'invoices'),
  string(name:'PREVIOUS_BUILD',defaultValue:'',description:'Predecessor receipt build for promotion; same-environment known-good build for rollback/drift'),
  string(name:'CHANGE_TICKET',defaultValue:''),
  booleanParam(name:'ALLOW_DELETIONS',defaultValue:false)
]), disableConcurrentBuilds(),buildDiscarder(logRotator(numToKeepStr:'200'))])
def targetEnv=env.TARGET_ENV
if (!(targetEnv in ['dev','uat','training','preprod','prod'])) error('Admin must fix TARGET_ENV on this job')
if (!(params.ACTION in ['DEPLOY','ROLLBACK'])) error('Invalid action')
if (!(params.PACKAGE_BUILD ==~ /[1-9][0-9]*/)) error('Package build required')
if (!(params.API ==~ /[a-z][a-z0-9-]{2,62}/)) error('Invalid API')
if (!(params.REF ==~ /kong-v\d+\.\d+\.\d+(-rc\d+)?/) && !(targetEnv=='dev' && params.REF ==~ /dev-[a-f0-9]{40}/)) error('Invalid release reference')
def automatic=targetEnv=='dev' && params.ACTION=='DEPLOY' && params.REF.startsWith('dev-') && !params.ALLOW_DELETIONS
if (!automatic && !(params.CHANGE_TICKET ==~ /[A-Za-z0-9][A-Za-z0-9_.-]{2,79}/)) error('Change/incident ticket required')
node(targetEnv in ['preprod','prod'] ? 'kong-prod' : 'kong-nonprod') {
  timeout(time:90,unit:'MINUTES') {
    lock(resource:"kong-delivery-${targetEnv}") {
    deleteDir()
    checkout scm
    def cfg=readJSON(file:'pipelines/settings.json')
    def target=cfg.targets[targetEnv]
    def packageDir="releases/${params.REF}/${params.API}"
    def evidenceDir='evidence/deployment'
    try {
      stage('Retrieve immutable package') {
        copyArtifacts(projectName:cfg.jobs.build,selector:specific(params.PACKAGE_BUILD),filter:"${packageDir}/**",fingerprintArtifacts:true)
      }
      def manifest=readJSON(file:"${packageDir}/manifest.json")
      if (!(manifest.tier in ['internal','external'])) error('Invalid API tier')
      def cp=target.control_planes[manifest.tier]
      if (!target.konnect_addr || !cp || !target.token_credential) error('Configure independent trusted target and credentials first')
      // Disabled sample packages are skipped only by automatic DEV; never silently retire live APIs.
      if (automatic && !manifest.environments.dev.enabled) {
        currentBuild.result='NOT_BUILT'
        echo "${params.API}: DEV disabled; no sync. Existing entities are unchanged."
        return
      }
      if (!automatic && (!target.approvers || (targetEnv in ['preprod','prod'] && !target.second_approvers))) error('Configure approval groups first')
      withEnv(["PACKAGE_BUILD=${params.PACKAGE_BUILD}","PACKAGE_DIR=${packageDir}","API=${params.API}","TARGET_ENV=${targetEnv}","EVIDENCE_DIR=${evidenceDir}","EXPECTED_CP=${cp}","EXPECTED_ADDR=${target.konnect_addr}","REF=${params.REF}","ALLOW_DELETIONS=${params.ALLOW_DELETIONS}","TRUSTED_AUTO_DEV=${automatic}"]) {
        // Fetch data identity on this trusted job; never execute candidate source scripts.
        stage('Verify Git identity') {
          if (!cfg.repository_url || !cfg.scm_credentials_id || !cfg.release_registry) error('Configure SCM identity and durable append-only release registry')
          dir('identity') {
            checkout([$class:'GitSCM',branches:[[name:'*/main']],userRemoteConfigs:[[url:cfg.repository_url,credentialsId:cfg.scm_credentials_id]],extensions:[[$class:'CloneOption',noTags:false,shallow:false]]])
            withEnv(["REQUIRE_SIGNED_TAG=${cfg.require_signed_tags}"]) {
              if (params.REF.startsWith('kong-v')) {
                sh 'bash ../scripts/verify-source.sh "$REF" > ../commit.txt; git rev-parse "refs/tags/$REF" > ../object.txt'
              } else {
                if (automatic) {
                  sh 'git rev-parse HEAD > ../commit.txt; cp ../commit.txt ../object.txt'
                } else {
                  sh 'commit=${REF#dev-}; git cat-file -e "$commit^{commit}"; git merge-base --is-ancestor "$commit" origin/main; printf "%s\\n" "$commit" > ../commit.txt; cp ../commit.txt ../object.txt'
                }
                // Reject stale queued automatic DEV builds after a newer main commit appears.
              }
            }
          }
          sh 'python3 scripts/release.py identity "$PACKAGE_DIR" "$REF" "$(cat commit.txt)" "$(cat object.txt)"'
          withEnv(["RELEASE_REGISTRY=${cfg.release_registry}"]) {
            lock(resource:'kong-release-registry') { sh 'python3 scripts/registry.py "$RELEASE_REGISTRY" "$PACKAGE_DIR"' }
          }
          sh 'python3 scripts/release.py verify "$PACKAGE_DIR" "$API" "$TARGET_ENV" "$EXPECTED_CP" "$EXPECTED_ADDR"'
        }
        if (!automatic && !(targetEnv=='dev' && params.ACTION=='DEPLOY')) {
          stage('Verify predecessor or known-good receipt') {
            if (!(params.PREVIOUS_BUILD ==~ /[1-9][0-9]*/)) error('Receipt build required')
            def predecessor=[uat:'dev',training:'dev',preprod:'uat',prod:'preprod'][targetEnv]
            def receiptEnv=params.ACTION=='ROLLBACK' ? targetEnv : predecessor
            if (!receiptEnv) error('Manual DEV changes use ROLLBACK or a reviewed release with deletion approval; see operations guide')
            copyArtifacts(projectName:cfg.jobs[receiptEnv],selector:specific(params.PREVIOUS_BUILD),filter:'evidence/public/deployment/receipt.json',target:'previous',fingerprintArtifacts:true)
                        withEnv(["RECEIPT_ACTION=${params.ACTION}"]) {
              sh 'python3 scripts/release.py receipt-check "$PACKAGE_DIR" "$TARGET_ENV" previous/evidence/public/deployment/receipt.json "$RECEIPT_ACTION"'
            }
          }
        }
        // One lock per CP/address across ALL writer jobs, not one lock per API.
        def lockKey="kong-${target.konnect_addr}-${cp}".replaceAll('[^A-Za-z0-9_.-]','_')
        lock(resource:lockKey) {
          withCredentials([string(credentialsId:target.token_credential,variable:'DECK_KONNECT_TOKEN')]) {
              def approvedGateway=target.smoke_gateways?.get(params.API)
              if (!approvedGateway || manifest.environments[targetEnv].gateway_url != approvedGateway) {
                error('Smoke destination must match the approved URL for this API and environment')
              }
              stage('Online schema validation and plan') { sh 'bash scripts/deploy.sh plan "$PACKAGE_DIR" "$API" "$TARGET_ENV" "$EVIDENCE_DIR"' }
              if (!automatic) {
                stage('Approve reviewed diff') {
                  sh 'python3 scripts/evidence.py "$EVIDENCE_DIR" evidence/public/deployment'
                  archiveArtifacts artifacts:'evidence/public/deployment/plan.json',fingerprint:true
                  def first=input(message:"${params.ACTION} ${params.REF} ${params.API} to ${targetEnv}; deletions=${params.ALLOW_DELETIONS}; ${params.CHANGE_TICKET}. Review plan.json.",submitter:target.approvers,submitterParameter:'APPROVER')
                  def approver=first instanceof Map ? first.APPROVER : first
                  if (targetEnv in ['preprod','prod']) {
                    def second=input(message:'Independent production approval',submitter:target.second_approvers,submitterParameter:'APPROVER')
                    def secondApprover=second instanceof Map ? second.APPROVER : second
                    if (secondApprover==approver) error('Two distinct approvers required')
                    writeJSON(file:"${evidenceDir}/second-approval.json",json:[approver:secondApprover])
                  }
                  withEnv(["APPROVER=${approver}","CHANGE_TICKET=${params.CHANGE_TICKET}"]) {
                    sh 'python3 scripts/release.py approve "$PACKAGE_DIR" "$EVIDENCE_DIR" "$API" "$TARGET_ENV" "$EXPECTED_CP" "$EXPECTED_ADDR" "$APPROVER" "$CHANGE_TICKET"'
                  }
                }
              }
              stage('Sync and smoke tests') {
                // Credential naming convention; configure these entries in the environment folder.
                withCredentials([string(credentialsId:"kong-smoke-${targetEnv}-${params.API}",variable:'SMOKE_BEARER_TOKEN')]) {
                  def phase=automatic ? 'auto-dev' : 'apply'
                  sh "bash scripts/deploy.sh ${phase} \"\$PACKAGE_DIR\" \"\$API\" \"\$TARGET_ENV\" \"\$EVIDENCE_DIR\""
                }
              }
              stage('Record successful delivery') {
                sh 'python3 scripts/release.py record "$PACKAGE_DIR" "$API" "$TARGET_ENV" "$EXPECTED_CP" "$EXPECTED_ADDR" "$EVIDENCE_DIR" "$BUILD_URL"'
              }
          }
        }
      }
    } finally {
      sh 'python3 scripts/evidence.py evidence/deployment evidence/public/deployment'
      archiveArtifacts artifacts:'evidence/public/deployment/**',allowEmptyArchive:true,fingerprint:true
      // Dumped live snapshots must stay on approved encrypted storage, never in these artifacts.
      deleteDir()
    }
  }
}
}
