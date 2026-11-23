#!/usr/bin/env python3
"""Company checks around native Kong YAML. decK remains the Kong schema validator."""
import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
import yaml

ROOT = Path(__file__).resolve().parents[1]
ENVS = ('dev', 'uat', 'training', 'preprod', 'prod')
NAME = re.compile(r'[a-z][a-z0-9-]{2,62}\Z')
VARIABLES = {'DECK_REDIS_HOST','DECK_REDIS_PORT','DECK_REDIS_PASSWORD_REF','DECK_CACHE_TOKENS_SALT','DECK_BACKEND_HOST','DECK_BACKEND_PORT','DECK_OIDC_ISSUER','DECK_OIDC_AUDIENCE','DECK_REQUIRED_ROLE','DECK_RATE_MINUTE','DECK_RATE_POLICY'}
TARGET_KEYS = {'enabled','konnect_addr','control_plane'}
VALUE_KEYS = {'enabled','gateway_url','variables'}

class UniqueLoader(yaml.SafeLoader): pass

def unique_mapping(loader, node, deep=False):
    result = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in result: raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(v, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def parse_yaml(text):
    try: return yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as exc: raise ValueError(f'invalid YAML: {exc}') from exc

def load(path):
    if Path(path).is_symlink(): raise ValueError(f'symlink not permitted: {path}')
    data = parse_yaml(Path(path).read_text())
    if not isinstance(data, dict): raise ValueError(f'expected mapping: {path}')
    return data

def check_keys(data, allowed, label):
    if not isinstance(data, dict): raise ValueError(f'{label}: expected mapping')
    unknown = set(data) - allowed
    if unknown: raise ValueError(f'{label}: unknown keys {sorted(unknown)}')
    missing = allowed - set(data)
    if missing: raise ValueError(f'{label}: missing keys {sorted(missing)}')

def identifier(value):
    if not isinstance(value, str) or not NAME.fullmatch(value): raise ValueError('invalid API identifier')
    return value

def integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high: raise ValueError(f'{label}: integer {low}..{high} required')

def https(value, label):
    u = urlparse(str(value))
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError(f'{label}: HTTPS URL without credentials/query/fragment required')

def placeholder(data):
    return any(t in json.dumps(data).upper() for t in ('REPLACE_', '.INVALID', 'CHANGE_ME', 'YOUR_'))

def require_enabled(target, values):
    if target.get('enabled') is not True or values.get('enabled') is not True:
        raise ValueError('deployment disabled: enable both target and API after review')

def environment_dir(root, env):
    if env not in ENVS: raise ValueError('invalid environment')
    return root/'environments'/('prod' if env in ('preprod','prod') else 'nonprod')/env

def values_path(root, env, domain, api):
    return environment_dir(root,env)/'apis'/domain/f'{api}.yaml'

def read_target(root, env):
    target = load(environment_dir(root,env)/'target.yaml')
    check_keys(target,TARGET_KEYS,'target')
    if type(target['enabled']) is not bool: raise ValueError('target enabled must be boolean')
    https(target['konnect_addr'],'konnect_addr')
    cp = target['control_plane']
    if not isinstance(cp,str) or not cp.strip() or any(c in cp for c in ('\n','\r','\0')):
        raise ValueError('invalid control plane name')
    return target

def api_directory(root, api):
    identifier(api)
    matches = list((root/'apis').glob(f'*/{api}'))
    if len(matches) != 1:
        raise ValueError(f'{api}: expected one API folder across all business domains')
    folder = matches[0]
    if folder.is_symlink() or folder.parent.is_symlink() or not folder.is_dir():
        raise ValueError(f'invalid API folder: {folder}')
    return folder

def settings(root, api, env, strict=False):
    identifier(api)
    if env not in ENVS: raise ValueError('invalid environment')
    folder = api_directory(root,api)
    meta = load(folder/'metadata.yaml')
    check_keys(meta, {'name','owner','team','domain','data_class','tier'}, 'metadata')
    if meta['name'] != api or meta['tier'] not in ('internal','external'): raise ValueError('metadata name/tier mismatch')
    if any(not isinstance(v,str) or not v.strip() for v in meta.values()): raise ValueError('metadata values must be nonempty strings')
    target = read_target(root,env)
    if meta['domain'] != folder.parent.name: raise ValueError('metadata domain must match business domain folder')
    values = load(values_path(root,env,folder.parent.name,api))
    check_keys(values,VALUE_KEYS,'environment API')
    if type(values['enabled']) is not bool: raise ValueError('enabled must be boolean')
    https(values['gateway_url'],'gateway_url')
    variables=values['variables']; check_keys(variables,VARIABLES,'variables')
    integer(variables['DECK_BACKEND_PORT'],'backend port',1,65535)
    integer(variables['DECK_RATE_MINUTE'],'minute quota',1,10000000)
    integer(variables['DECK_REDIS_PORT'],'Redis port',1,65535)
    if variables['DECK_RATE_POLICY'] not in ('local','redis'): raise ValueError('rate policy must be local or redis')
    for key, value in variables.items():
        if not isinstance(value,(str,int)) or isinstance(value,bool) or any(c in str(value) for c in ('\0','\n','\r')):
            raise ValueError(f'invalid environment variable: {key}')
    if not re.fullmatch(r'[A-Za-z0-9.-]+', str(variables['DECK_BACKEND_HOST'])): raise ValueError('invalid backend hostname')
    https(variables['DECK_OIDC_ISSUER'],'OIDC issuer')
    if not variables['DECK_OIDC_AUDIENCE'] or not variables['DECK_REQUIRED_ROLE']: raise ValueError('audience and role required')
    if strict or (target['enabled'] and values['enabled']):
        require_enabled(target,values)
        if placeholder((meta,target,values)): raise ValueError('replace sample placeholders before deployment')
    return meta,target,values

def validate_state(state, api, tier, env):
    """Enforce the supported company baseline; decK validates full plugin schemas."""
    if '${{' in json.dumps(state): raise ValueError('unresolved environment template')
    if set(state)-{'_format_version','_info','services'}: raise ValueError('unexpected top-level entity: shared objects require separate scope')
    tag=f'owner-{api}'
    if state.get('_info',{}).get('select_tags') != [tag]: raise ValueError('ownership scope mismatch')
    def owner_tags(value):
        if isinstance(value,dict):
            if 'tags' in value:
                owners=[t for t in value['tags'] if str(t).startswith('owner-')]
                if owners!=[tag]: raise ValueError('ownership tags must identify only this API')
            for item in value.values():owner_tags(item)
        elif isinstance(value,list):
            for item in value:owner_tags(item)
    owner_tags(state)
    services=state.get('services')
    if not isinstance(services,list) or len(services)!=1: raise ValueError('one Service per API required')
    service=services[0]
    if tag not in service.get('tags',[]): raise ValueError('Service ownership tag missing')
    if service.get('tls_verify') is not True: raise ValueError('upstream TLS verification required')
    if service.get('protocol')!='https': raise ValueError('backend HTTPS required by this baseline')
    integer(service.get('port'),'port',1,65535)
    if not re.fullmatch(r'[A-Za-z0-9.-]+',str(service.get('host',''))): raise ValueError('invalid Service host')
    for key in ('connect_timeout','read_timeout','write_timeout'): integer(service.get(key),key,1,600000)
    integer(service.get('retries'),'retries',0,5)
    routes=service.get('routes',[])
    if not routes: raise ValueError('at least one Route required')
    for route in routes:
        if tag not in route.get('tags',[]): raise ValueError('Route ownership tag missing')
        if route.get('protocols')!=['https']: raise ValueError('HTTPS Routes required')
        if not route.get('methods') or any(m not in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS') for m in route['methods']): raise ValueError('explicit HTTP methods required')
        if not route.get('paths') or any(not re.fullmatch(r'/[a-z0-9-]+/[a-z0-9-]+/v[1-9][0-9]*(?:/[A-Za-z0-9_./-]*)?',p) for p in route['paths']): raise ValueError('Route paths must follow /domain/api/v1/...')
        if type(route.get('strip_path')) is not bool or type(route.get('preserve_host')) is not bool: raise ValueError('explicit Route booleans required')
        if route.get('plugins'): raise ValueError('Route-level plugins require reviewed extension; cannot bypass Service baseline')
    plugins=service.get('plugins',[])
    names=[p.get('name') for p in plugins]
    approved = {
        'correlation-id', 'cors', 'ip-restriction', 'oas-validation',
        'openid-connect', 'rate-limiting', 'request-size-limiting',
    }
    if set(names)-approved: raise ValueError('plugin not in approved baseline')
    if any('https' not in p.get('protocols',['http','https']) for p in plugins): raise ValueError('Service plugins must cover HTTPS')
    if any(any(k in p for k in ('consumer','consumer_group','route','service')) for p in plugins): raise ValueError('baseline plugin scope cannot narrow its parent Service')
    if any(p.get('enabled',True) is not True for p in plugins): raise ValueError('disabled baseline plugin rejected')
    def secrets(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in ('client_secret','password','session_secret','private_key','redis_password'):
                    vals=item if isinstance(item,list) else [item]
                    if any(not isinstance(v,str) or not v.startswith('{vault://') or not v.endswith('}') for v in vals): raise ValueError('plaintext secret rejected; use supported Vault reference')
                secrets(item)
        elif isinstance(value,list):
            for item in value:secrets(item)
    secrets(state)
    if len(set(names))!=len(names): raise ValueError('duplicate Service plugin')
    if any(tag not in p.get('tags',[]) for p in plugins): raise ValueError('plugin ownership tag missing')
    for required in ('openid-connect','rate-limiting','request-size-limiting','correlation-id'):
        if required not in names: raise ValueError(f'required plugin missing: {required}')
    byname={p['name']:p.get('config',{}) for p in plugins}
    auth=byname['openid-connect']
    if auth.get('auth_methods')!=['bearer'] or auth.get('anonymous'): raise ValueError('bearer-only authentication required')
    if auth.get('ssl_verify',True) is not True: raise ValueError('OIDC TLS verification required')
    if not auth.get('audience_required'): raise ValueError('audience_required missing')
    if not auth.get('roles_required') and not auth.get('scopes_required'): raise ValueError('authorization: role or scope required')
    https(auth.get('issuer'),'OIDC issuer')
    rate=byname['rate-limiting']
    integer(rate.get('minute'),'rate minute',1,10000000)
    if rate.get('limit_by')!='service': raise ValueError('baseline uses Service-scoped quota; Consumer quotas need separate identity design')
    if rate.get('policy') not in ('local','redis'): raise ValueError('Konnect rate policy must be local or redis')
    if rate.get('policy')=='redis':
        redis=rate.get('redis',{})
        if not redis.get('host') or redis.get('ssl') is not True or redis.get('ssl_verify') is not True: raise ValueError('Redis requires explicit host and verified TLS')
        integer(redis.get('port'),'Redis port',1,65535)
        if not str(redis.get('password','')).startswith('{vault://'): raise ValueError('Redis requires a supported Vault password reference')
    if env in ('preprod','prod') and rate.get('policy')!='redis': raise ValueError('PREPROD/PROD baseline requires reviewed distributed Redis quota')
    size=byname['request-size-limiting']
    integer(size.get('allowed_payload_size'),'payload size',1,100)
    if size.get('size_unit')!='megabytes': raise ValueError('payload size unit must be megabytes')
    if tier=='external':
        for p in ('ip-restriction','oas-validation'):
            if p not in names: raise ValueError(f'external API requires {p}')
        networks=byname['ip-restriction'].get('allow',[])
        if not networks: raise ValueError('external allow list required')
        for n in networks:
            if ipaddress.ip_network(n,strict=False).prefixlen==0: raise ValueError('external allow list cannot allow the entire Internet')
    if placeholder(state): raise ValueError('rendered state contains placeholder')

def path_methods(spec, item):
    methods = {'get', 'head', 'post', 'put', 'patch', 'delete', 'options', 'trace'}
    result = set()
    visited = set()
    while isinstance(item, dict):
        result.update(methods.intersection(item))
        if '$ref' not in item:
            return result
        ref = item['$ref']
        if not isinstance(ref, str) or not ref.startswith('#/') or ref in visited:
            raise ValueError(f'invalid or circular local OpenAPI path reference: {ref}')
        visited.add(ref)
        item = spec
        for token in unquote(ref[2:]).split('/'):
            key = token.replace('~1', '/').replace('~0', '~')
            if not isinstance(item, dict) or key not in item:
                raise ValueError(f'unknown OpenAPI path reference: {ref}')
            item = item[key]
    raise ValueError('expected an OpenAPI Path Item Object')

def contract(state,spec,tests):
    for service in state['services']:
        for plugin in service.get('plugins',[]):
            if plugin['name']=='oas-validation' and parse_yaml(plugin.get('config',{}).get('api_spec',''))!=spec:
                raise ValueError('embedded OpenAPI differs from openapi.yaml')
    paths=spec.get('paths',{})
    if not str(spec.get('openapi','')).startswith('3.'): raise ValueError('OpenAPI 3 required')
    documented = set()
    for path, item in paths.items():
        if not path.startswith('/'):  # OpenAPI allows extensions on the Paths Object.
            continue
        documented.update((method.upper(), path) for method in path_methods(spec,item))
    operations = {
        (method, path)
        for service in state['services']
        for route in service['routes']
        for path in route['paths']
        for method in route['methods']
    }
    for label, missing in [('OpenAPI operation', operations - documented),
                           ('Kong route', documented - operations)]:
        if missing:
            details = ', '.join(f'{method} {path}' for method, path in sorted(missing))
            raise ValueError(f'{label} missing: {details}')
    if not isinstance(tests,list) or not tests: raise ValueError('API tests required')
    modes=set()
    untested = {operation for operation in operations if operation[0] in ('GET','HEAD')}
    for t in tests:
        check_keys(t,{'name','method','path','auth','expected_status','body_contains'},'test')
        if t['method'] not in ('GET','HEAD'): raise ValueError('smoke tests must be read-only GET or HEAD')
        if not isinstance(t['name'],str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',t['name']): raise ValueError('invalid smoke test name')
        if (t['method'],t['path']) not in operations: raise ValueError('test must reference a declared operation')
        if t['auth'] not in ('valid','none','invalid'): raise ValueError('test auth must be valid, none or invalid')
        integer(t['expected_status'],'HTTP status',100,599)
        if not isinstance(t['body_contains'],str): raise ValueError('body_contains must be string')
        if t['auth']=='valid' and not 200<=t['expected_status']<300: raise ValueError('positive test must expect 2xx')
        if t['auth']!='valid' and t['expected_status'] not in (401,403): raise ValueError('negative auth test must expect rejection')
        if t['auth']=='valid':
            untested.discard((t['method'],t['path']))
        modes.add(t['auth'])
    if modes!={'valid','none','invalid'}: raise ValueError('tests must include valid, missing and invalid credentials')
    if untested:
        details = ', '.join(f'{method} {path}' for method, path in sorted(untested))
        raise ValueError(f'successful smoke test missing: {details}')

def validate_openapi(spec):
    # Resolve internal document references only; validation must not read local files or fetch URLs.
    def local_refs(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='$ref' and (not isinstance(item,str) or not item.startswith('#/')):
                    raise ValueError('OpenAPI references must be local to this document; bundle external references first')
                local_refs(item)
        elif isinstance(value,list):
            for item in value:local_refs(item)
    local_refs(spec)
    from openapi_spec_validator import validate
    try:validate(spec)
    except Exception as exc:raise ValueError(f'OpenAPI schema invalid: {exc}') from exc


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('env'); e.add_argument('api'); e.add_argument('env',choices=ENVS); e.add_argument('--strict',action='store_true')
    s=sub.add_parser('state'); s.add_argument('api'); s.add_argument('env',choices=ENVS); s.add_argument('file',type=Path); s.add_argument('--draft',action='store_true')
    scope=sub.add_parser('scope'); scope.add_argument('api'); scope.add_argument('file',type=Path)
    sub.add_parser('source')
    sub.add_parser('directory').add_argument('api')
    a=p.parse_args()
    try:
        if a.command=='directory':
            print(api_directory(a.root,a.api))
        elif a.command=='env':
            _,_,v=settings(a.root,a.api,a.env,a.strict)
            for k,val in v['variables'].items(): sys.stdout.buffer.write(k.encode()+b'\0'+str(val).encode()+b'\0')
        elif a.command=='scope':
            identifier(a.api)
            expected={'select_tags':[f'owner-{a.api}']}
            native=load(api_directory(a.root,a.api)/'kong.yaml')
            if native.get('_info')!=expected: raise ValueError('source ownership scope mismatch')
            state=load(a.file); state['_info']=expected
            a.file.write_text(yaml.safe_dump(state,sort_keys=False))
        elif a.command=='state':
            m,t,v=settings(a.root,a.api,a.env)
            state=load(a.file)
            # Disabled draft targets may contain illustrative values and local counters.
            draft=a.draft and not (t['enabled'] and v['enabled'])
            check_env='dev' if draft else a.env
            if draft:
                text=json.dumps(state).replace('REPLACE_','DEMO_').replace('.invalid','.example.com')
                state=json.loads(text)
            validate_state(state,a.api,m['tier'],check_env)
            contract(state,load(api_directory(a.root,a.api)/'openapi.yaml'),load(api_directory(a.root,a.api)/'tests.yaml')['tests'])
            print(f'Policy and contract checks passed: {a.api}/{a.env}')
        else:
            for env in ENVS:
                read_target(a.root,env)
            seen_names=set(); seen_paths=set()
            for folder in sorted((a.root/'apis').glob('*/*')):
                if not folder.is_dir(): continue
                for env in ENVS: settings(a.root,folder.name,env)
                validate_openapi(load(folder/'openapi.yaml'))
                native=load(folder/'kong.yaml')
                for svc in native.get('services',[]):
                    if svc['name'] in seen_names: raise ValueError('duplicate Service name across APIs')
                    seen_names.add(svc['name'])
                    for r in svc.get('routes',[]):
                        if r['name'] in seen_names: raise ValueError('duplicate entity name across APIs')
                        seen_names.add(r['name'])
                        for path in r['paths']:
                            if path in seen_paths: raise ValueError('duplicate Route path across APIs')
                            seen_paths.add(path)
            print('Source metadata and environment checks passed')
    except (ValueError,KeyError,TypeError,OSError) as exc:
        sys.exit(f'VALIDATION FAILED: {exc}')

if __name__=='__main__': main()
