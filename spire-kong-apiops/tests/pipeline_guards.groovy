// Run with Groovy 2.4+; no Jenkins controller, credentials or network calls.
// These are guard checks, not a substitute for Jenkins Pipeline DSL/CPS acceptance.
class GuardRejected extends RuntimeException { GuardRejected(String x) { super(x) } }
class AgentReached extends RuntimeException {}
def source=new File(args ? args[0] : 'pipelines/Deploy.Jenkinsfile').text
def execute={ Map overrides, String target ->
  def loader=new GroovyClassLoader()
  def instance=loader.parseClass(source).newInstance()
  instance.binding=new Binding([params:[ACTION:'DEPLOY',PACKAGE_BUILD:'12',API:'documents',REF:'kong-v1.0.0',PREVIOUS_BUILD:'1',CHANGE_TICKET:'CHG-123',ALLOW_DELETIONS:false]+overrides,env:[TARGET_ENV:target]])
  instance.metaClass.methodMissing={ String name, Object values ->
    if (name=='error') throw new GuardRejected(values[0].toString())
    if (name=='node') throw new AgentReached()
    null
  }
  try { instance.run(); assert false:'Pipeline did not stop at a guard or agent' }
  catch (GuardRejected reject) { return reject.message }
  catch (AgentReached accepted) { return 'agent' }
}
assert execute([ACTION:'DRIFT'],'uat').contains('Invalid action')
assert execute([API:'../../escape'],'uat').contains('Invalid API')
assert execute([PACKAGE_BUILD:'lastSuccessfulBuild'],'uat').contains('Package build required')
assert execute([REF:'dev-'+('a'*40)],'prod').contains('Invalid release')
assert execute([:],'unknown').contains('TARGET_ENV')
assert execute([CHANGE_TICKET:''],'prod').contains('ticket')
assert execute([:],'uat')=='agent'
assert execute([REF:'dev-'+('a'*40),CHANGE_TICKET:''],'dev')=='agent'
println('PASS: 8 deployment entry guards; no agent allocation or external side effects')
