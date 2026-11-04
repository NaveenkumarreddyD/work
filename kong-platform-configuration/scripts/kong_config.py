#!/usr/bin/env python3
"""Validated, deterministic single-API decK state generator; never loads secrets."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
import yaml

ROOT = Path(__file__).resolve().parents[1]
ENVS = ('dev', 'uat', 'training', 'preprod', 'prod')
NAME = re.compile(r'^[a-z][a-z0-9-]{2,62}$')
PATH = re.compile(r'^/[a-z0-9-]+/[a-z0-9-]+/v[1-9][0-9]*(?:/[A-Za-z0-9_{}./-]*)?$')
BLOCKED = ('REPLACE', '.invalid', 'YOUR_', 'CHANGE_ME')

def read_yaml(path):
    if not path.is_file():
        raise ValueError(f'Missing file: {path.relative_to(ROOT)}')
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Expected a YAML mapping: {path}')
    return data

def assert_url(value, label, require_https=True):
    if not isinstance(value, str) or not value:
        raise ValueError(f'{label} must be a URL')
    u = urlparse(value)
    if u.scheme not in (('https',) if require_https else ('http', 'https')) or not u.hostname or u.username or u.password or u.fragment:
        raise ValueError(f'{label} must be a valid {"HTTPS" if require_https else "HTTP(S)"} URL without credentials')

def check(api, env, strict=False):
    if not NAME.fullmatch(api):
        raise ValueError('API name must be lower-case kebab-case and at least 3 characters')
    if env not in ENVS:
        raise ValueError(f'Invalid environment: {env}')
    a = read_yaml(ROOT/'apis'/api/'api.yaml')
    e = read_yaml(ROOT/'environments'/env/'environment.yaml')
    v = read_yaml(ROOT/'environments'/env/'values'/f'{api}.yaml')
    if a.get('name') != api:
        raise ValueError('api.yaml name must match API directory')
    if e.get('name') != env or not isinstance(e.get('enabled'), bool):
        raise ValueError('Invalid environment config')
    tier = a.get('tier')
    if tier not in ('internal', 'external'):
        raise ValueError('tier must be internal or external')
    if not a.get('team') or not a.get('owner'):
        raise ValueError('API team and owner required')
    service = a.get('service')
    if not isinstance(service, dict) or not NAME.fullmatch(str(service.get('name', ''))):
        raise ValueError('Service name must be kebab-case')
    if not all(isinstance(service.get(k), int) and not isinstance(service.get(k), bool) and 0 <= service[k] <= 600000 for k in ('connect_timeout', 'read_timeout', 'write_timeout', 'retries')):
        raise ValueError('Service timeouts/retries must be explicit nonnegative integers')
    routes = a.get('routes')
    if not isinstance(routes, list) or not routes:
        raise ValueError('At least one Route is required')
    names=set(); paths=set()
    for r in routes:
        if not isinstance(r, dict) or not NAME.fullmatch(str(r.get('name', ''))):
            raise ValueError('Each Route needs a kebab-case name')
        if r['name'] in names: raise ValueError('Duplicate Route name')
        names.add(r['name'])
        if not isinstance(r.get('paths'), list) or not r['paths']:
            raise ValueError('Each Route needs paths')
        for path in r['paths']:
            if not isinstance(path,str) or not PATH.fullmatch(path):
                raise ValueError(f'Route path must follow /domain/api/v1/...: {path}')
            if path in paths: raise ValueError('Duplicate Route path')
            paths.add(path)
        if not isinstance(r.get('methods'), list) or not r['methods'] or any(m not in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS') for m in r['methods']):
            raise ValueError('Route methods must be explicit allowed HTTP verbs')
        if not isinstance(r.get('strip_path'),bool) or not isinstance(r.get('preserve_host'),bool):
            raise ValueError('Route strip_path and preserve_host must be explicit booleans')
    assert_url(v.get('backend_url'), 'backend_url', False)
    assert_url(v.get('gateway_url'), 'gateway_url')
    assert_url(v.get('oidc_issuer'), 'oidc_issuer')
    if not isinstance(v.get('oidc_audience'),str) or not v['oidc_audience']:
        raise ValueError('oidc_audience required')
    if v.get('smoke_path') not in paths or not isinstance(v.get('smoke_expected_status'),int):
        raise ValueError('smoke_path must be one of the configured paths, and status must be integer')
    assert_url(e.get('konnect_addr'), 'konnect_addr')
    cp = e.get('control_planes',{}).get(tier)
    if not isinstance(cp,str) or not cp:
        raise ValueError('Missing tier-specific Control Plane')
    if strict:
        if not e['enabled']:
            raise ValueError(f'{env} disabled. Platform team must enable it explicitly.')
        if a.get('approved_for_deployment') is not True:
            raise ValueError('API not approved for deployment')
        vals=[a.get('owner'), cp, v['backend_url'], v['gateway_url'], v['oidc_issuer'], v['oidc_audience']]
        if any(any(block in str(x).upper() for block in BLOCKED) for x in vals):
            raise ValueError('Deployment blocked: replace all sample/placeholder values')
    return a,e,v,cp

def build(api, env, strict=False):
    a,e,v,cp = check(api,env,strict)
    owner_tag=f'owner-{api}'
    url=urlparse(v['backend_url'])
    service=dict(a['service'])
    service.update(protocol=url.scheme,host=url.hostname,port=url.port or (443 if url.scheme=='https' else 80),path=url.path or None, tags=[owner_tag,f'team-{a["team"]}',f'tier-{a["tier"]}'])
    service={k:val for k,val in service.items() if val is not None}
    service['routes'] = []
    for route in a['routes']:
        r={k:route[k] for k in ('name','paths','methods','strip_path','preserve_host')}
        r['tags']=[owner_tag]
        service['routes'].append(r)
    service['plugins']=[{
        'name':'openid-connect',
        'tags':[owner_tag],
        'config':{
            'issuer':v['oidc_issuer'],
            'audience':[v['oidc_audience']],
            'auth_methods':['bearer'],
        },
    }]
    state={'_format_version':'3.0','_info':{'select_tags':[owner_tag]},'services':[service]}
    return state,{'environment':env,'api':api,'tier':a['tier'],'control_plane':cp,'konnect_addr':e['konnect_addr'],'gateway_url':v['gateway_url'],'smoke_path':v['smoke_path'],'smoke_expected_status':v['smoke_expected_status'],'ownership_tag':owner_tag}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api',required=True)
    p.add_argument('--env',required=True,choices=ENVS)
    p.add_argument('--out',default='build/state.yaml')
    p.add_argument('--strict',action='store_true',help='Require real approved deployment configuration')
    args=p.parse_args()
    try:
        state,meta=build(args.api,args.env,args.strict)
        out=Path(args.out)
        out.parent.mkdir(parents=True,exist_ok=True)
        payload=yaml.safe_dump(state,sort_keys=True)
        out.write_text(payload,encoding='utf-8')
        manifest=out.with_suffix('.manifest.json')
        meta['sha256']=hashlib.sha256(payload.encode('utf-8')).hexdigest()
        manifest.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(f'Rendered {out}, hash={meta["sha256"]}, scope={meta["ownership_tag"]}')
    except (ValueError, KeyError, yaml.YAMLError) as ex:
        print(f'CONFIG ERROR: {ex}',file=sys.stderr)
        sys.exit(1)

if __name__=='__main__': main()
