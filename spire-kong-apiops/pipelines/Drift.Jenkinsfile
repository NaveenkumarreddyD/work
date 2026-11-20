// Standalone ADMIN-PINNED trusted job. Optional schedule; no sync or auto-remediation.
properties([pipelineTriggers([cron('H 3 * * *')]),disableConcurrentBuilds(),buildDiscarder(logRotator(numToKeepStr:'60'))])
def cfg
def targets
node('kong-validate') {
  deleteDir();checkout scm
  cfg=readJSON(file:'pipelines/settings.json')
  targets=cfg.drift_targets
}
if (!targets) error('Configure drift_targets explicitly; no targets have been invented')
def failures=[]
for (item in targets) {
  def targetEnv=item.environment
  def api=item.api
  if (!(targetEnv in ['dev','uat','training','preprod','prod']) || !(api ==~ /[a-z][a-z0-9-]{2,62}/)) error('Invalid drift target')
  node(targetEnv in ['preprod','prod'] ? 'kong-prod' : 'kong-nonprod') {
    timeout(time:15,unit:'MINUTES') {
      lock(resource:"kong-delivery-${targetEnv}") {
      deleteDir();checkout scm
      def evidenceDir='evidence/deployment'
      try {
        // Parameter filter selects the API's latest successful delivery, including successful rollback.
        // Failed partial syncs do not advance this baseline. Missing history is an actionable failure.
        copyArtifacts(projectName:cfg.jobs[targetEnv],selector:lastSuccessful(),parameters:"API=${api}",filter:'evidence/public/deployment/receipt.json',target:'last',fingerprintArtifacts:true)
        def receipt=readJSON(file:'last/evidence/public/deployment/receipt.json')
        if (!(receipt.package_build ==~ /[1-9][0-9]*/) || receipt.api!=api || receipt.environment!=targetEnv) error('Invalid delivery history')
        if (!(receipt.tag ==~ /kong-v\d+\.\d+\.\d+(-rc\d+)?/) && !(targetEnv=='dev' && receipt.tag ==~ /dev-[a-f0-9]{40}/)) error('Invalid deployed ref')
        def packageDir="releases/${receipt.tag}/${api}"
        copyArtifacts(projectName:cfg.jobs.build,selector:specific(receipt.package_build),filter:"${packageDir}/**",fingerprintArtifacts:true)
        def manifest=readJSON(file:"${packageDir}/manifest.json")
        if (!(manifest.tier in ['internal','external'])) error('Invalid tier')
        def target=cfg.targets[targetEnv]
        def cp=target.control_planes[manifest.tier]
        if (!cp || !target.konnect_addr || !target.token_credential || !cfg.release_registry) error('Configure trusted drift target')
        withEnv(["PACKAGE_DIR=${packageDir}","API=${api}","TARGET_ENV=${targetEnv}","EVIDENCE_DIR=${evidenceDir}","EXPECTED_CP=${cp}","EXPECTED_ADDR=${target.konnect_addr}","RELEASE_REGISTRY=${cfg.release_registry}"]) {
          sh 'python3 scripts/release.py receipt-check "$PACKAGE_DIR" "$TARGET_ENV" last/evidence/public/deployment/receipt.json ROLLBACK'
          sh 'python3 scripts/release.py verify "$PACKAGE_DIR" "$API" "$TARGET_ENV" "$EXPECTED_CP" "$EXPECTED_ADDR"'
          lock(resource:'kong-release-registry') { sh 'python3 scripts/registry.py "$RELEASE_REGISTRY" "$PACKAGE_DIR"' }
          def lockKey="kong-${target.konnect_addr}-${cp}".replaceAll('[^A-Za-z0-9_.-]','_')
          lock(resource:lockKey) {
            // Prefer a read-only token in a separately installed drift job/folder.
            withCredentials([string(credentialsId:target.token_credential,variable:'DECK_KONNECT_TOKEN')]) {
              sh 'bash scripts/deploy.sh drift "$PACKAGE_DIR" "$API" "$TARGET_ENV" "$EVIDENCE_DIR"'
            }
          }
        }
      } catch (Exception problem) {
        if (problem.class.name=='org.jenkinsci.plugins.workflow.steps.FlowInterruptedException') throw problem
        echo "Drift check failed for ${api}/${targetEnv}; inspect restricted build evidence"
        failures.add("${api}/${targetEnv}")
      } finally {
        sh 'python3 scripts/evidence.py evidence/deployment evidence/public/deployment'
        archiveArtifacts artifacts:'evidence/public/deployment/**',allowEmptyArchive:true,fingerprint:true
        deleteDir()
      }
      }
    }
  }
}
if (failures) error("Drift or connectivity/history failure: ${failures.join(', ')}")
