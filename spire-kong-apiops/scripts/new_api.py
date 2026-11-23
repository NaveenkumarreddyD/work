#!/usr/bin/env python3
"""Create editable native API files once. Never deploys or enables an environment."""
import argparse
from pathlib import Path
import re
import secrets
import sys
import yaml
from validate import ENVS, ROOT, identifier, load

class ReadableYaml(yaml.SafeDumper):
    """Keep embedded OpenAPI readable and Vault substitutions quoted."""

def readable_string(dumper, value):
    style='|' if '\n' in value else None
    if value == '${{ env "DECK_REDIS_PASSWORD_REF" }}': style="'"
    return dumper.represent_scalar('tag:yaml.org,2002:str',value,style=style)

ReadableYaml.add_representer(str,readable_string)

def dump(value):
    return yaml.dump(value,Dumper=ReadableYaml,sort_keys=False,width=100)

def create_api(root, *, name, path, owner, team='integrations', tier='internal', body_contains=''):
    """Create four API files plus five disabled values files; refuse all collisions."""
    root=Path(root)
    identifier(name)
    if tier not in ('internal','external'): raise ValueError('tier must be internal or external')
    if not re.fullmatch(r'/[a-z0-9-]+/[a-z0-9-]+/v[1-9][0-9]*(?:/[A-Za-z0-9_./-]*)?',path):
        raise ValueError('path must look like /crm/customers/v1')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',owner): raise ValueError('owner must be a team email address')
    if not re.fullmatch(r'[a-z][a-z0-9-]*',team): raise ValueError('team must use lower-case letters, numbers and hyphens')
    if not isinstance(body_contains,str) or '\0' in body_contains: raise ValueError('response text cannot contain NUL')
    api_dir=root/'apis'/name
    destinations=[api_dir/f for f in ('metadata.yaml','kong.yaml','openapi.yaml','tests.yaml')]
    destinations += [root/'apis'/name/'overlays'/f'{env}.yaml' for env in ENVS]
    if api_dir.exists() or api_dir.is_symlink(): raise ValueError(f'API already exists: {name}; no files changed')
    for dest in destinations:
        if dest.exists() or dest.is_symlink(): raise ValueError(f'file already exists: {dest}; no files changed')
        for parent in (dest,*dest.parents):
            if parent.is_symlink(): raise ValueError(f'symlink rejected: {parent}')
            if parent==root: break
    # A newcomer should discover a duplicate public path before generating nine files.
    for existing in (root/'apis').glob('*/metadata.yaml'):
        if load(existing)['tier']!=tier: continue
        for service in load(existing.with_name('kong.yaml')).get('services',[]):
            if any(path in route.get('paths',[]) for route in service.get('routes',[])):
                raise ValueError(f'path already used by {existing.parent.name} on the {tier} tier')
    domain=path.split('/')[1]; classification='internal' if tier=='internal' else 'confidential'
    tag=f'owner-{name}'
    metadata=dict(name=name,owner=owner,team=team,domain=domain,data_class=classification,tier=tier)
    spec={'openapi':'3.0.3','info':{'title':name.replace('-',' ').title(),'version':'1.0.0'},'paths':{path:{'get':{
        'summary':f'Read {name}', 'security':[{'bearerAuth':[]}],
        'responses':{'200':{'description':'Successful response'},'401':{'description':'Authentication rejected'},'403':{'description':'Permission rejected'}}}}},
        'components':{'securitySchemes':{'bearerAuth':{'type':'http','scheme':'bearer','bearerFormat':'JWT'}}}}
    native=load(root/'scripts/templates'/f'{tier}.kong.yaml')
    native['_info']={'select_tags':[tag]}
    service=native['services'][0]; service['name']=f'{name}-service'
    service['tags']=[tag,f'team-{team}',f'domain-{domain}',f'data-{classification}']
    route=service['routes'][0]; route.update(name=f'{name}-v1',paths=[path],methods=['GET'],tags=[tag])
    for plugin in service['plugins']:
        plugin['tags']=[tag]
        if plugin['name']=='oas-validation':plugin['config']['api_spec']='${{ env "DECK_OPENAPI_SPEC" }}'
    tests={'tests':[{'name':label,'method':'GET','path':path,'auth':auth,'expected_status':status,'body_contains':body_contains if auth=='valid' else ''}
                    for label,auth,status in [('authenticated-read','valid',200),('missing-token-rejected','none',401),('invalid-token-rejected','invalid',401)]]}
    native_text=dump(native)
    native_text=native_text.replace('_info:\n','# Management boundary: never reuse another API\'s owner tag.\n_info:\n',1)
    native_text=native_text.replace('services:\n','# Service = destination backend. Variables come from apis/<api>/overlays/.\nservices:\n',1)
    native_text=native_text.replace('  routes:\n','  # Route = public request path and HTTP method. Update openapi.yaml too.\n  routes:\n',1)
    native_text=native_text.replace('  plugins:\n','  # Policies apply to every Route on this Service. Review docs/OPERATIONS.md.\n  plugins:\n',1)
    content={destinations[0]:'# Ownership and classification; no passwords or tokens.\n'+dump(metadata),
             destinations[1]:'# EDIT THIS FILE: native Kong configuration, not generated deployment output.\n'+native_text,
             destinations[2]:'# API contract. Keep paths/methods aligned with kong.yaml.\n'+dump(spec),
             destinations[3]:'# Replace the success body assertion with a real stable response property.\n'+dump(tests)}
    for env,dest in zip(ENVS,destinations[4:]):
        values=load(root/'scripts/templates/environment.yaml')
        values['enabled']=False
        values['gateway_url']=f'https://REPLACE_{env.upper()}_GATEWAY.example.invalid'
        v=values['variables']
        v.update(DECK_BACKEND_HOST=f'replace-{env}-{name}-backend.example.invalid',
                 DECK_OIDC_AUDIENCE=f'api://REPLACE_{env.upper()}_{name.upper().replace("-","_")}_AUDIENCE',
                 DECK_REQUIRED_ROLE='REPLACE_APPROVED_APPLICATION_ROLE',
                 DECK_CACHE_TOKENS_SALT=secrets.token_hex(16),
                 DECK_REDIS_HOST=f'replace-{env}-redis.example.invalid',
                 DECK_REDIS_PASSWORD_REF=f'{{vault://REPLACE_VAULT_PREFIX/redis-{env}-password}}')
        value_text=dump(values)
        descriptions={'gateway_url':'Front door clients call through F5/Kong; not the backend.',
                      'DECK_BACKEND_HOST':'Backend hostname only: no https:// and no path.',
                      'DECK_OIDC_ISSUER':'Ask IAM for the actual access-token issuer, audience and role.',
                      'DECK_RATE_POLICY':'local is per node; PREPROD/PROD require reviewed Redis counters.',
                      'DECK_CACHE_TOKENS_SALT':'Keep this public salt stable. It is not an authentication secret.',
                      'DECK_REDIS_PASSWORD_REF':'Supported Vault reference only; never paste the password.'}
        lines=[]
        for line in value_text.splitlines():
            key=line.strip().split(':',1)[0]
            if key in descriptions:lines.append(' '*(len(line)-len(line.lstrip()))+'# '+descriptions[key])
            lines.append(line)
        content[dest]='# Start here for environment values. Keep disabled until platform review.\n'+'\n'.join(lines)+'\n'
    created=[];created_dirs=[]
    try:
        for dest,text in content.items():
            pending=[];parent=dest.parent
            while not parent.exists():pending.append(parent);parent=parent.parent
            for directory in reversed(pending):directory.mkdir();created_dirs.append(directory)
            # Exclusive creation protects existing work even if it appears after preflight.
            with dest.open('x',encoding='utf-8') as stream:
                created.append(dest);stream.write(text)
    except (OSError,ValueError):
        for dest in reversed(created):dest.unlink()
        for directory in reversed(created_dirs):directory.rmdir()
        raise
    return created

def main():
    parser=argparse.ArgumentParser(description=__doc__,epilog='Example: python3 scripts/new_api.py --name customer-api --path /crm/customers/v1 --owner team@example.com --body-contains customers')
    parser.add_argument('--name');parser.add_argument('--path');parser.add_argument('--owner');parser.add_argument('--team',default='integrations')
    parser.add_argument('--tier',choices=('internal','external'),default='internal');parser.add_argument('--body-contains',default='')
    args=parser.parse_args()
    if not all((args.name,args.path,args.owner)):
        if not sys.stdin.isatty():parser.error('Provide --name, --path and --owner, or run in a terminal for guided questions')
        print('Create a draft API. This only creates files; it cannot deploy.\nInitial endpoint: GET. No passwords or tokens are requested.')
        args.name=args.name or input('API name, for example customer-api: ').strip()
        args.path=args.path or input('Public path, for example /crm/customers/v1: ').strip()
        args.owner=args.owner or input('Owning team email: ').strip()
        args.team=input(f'Team name [{args.team}]: ').strip() or args.team
        args.tier=input(f'Gateway tier internal/external [{args.tier}]: ').strip() or args.tier
        args.body_contains=input('Text expected in a successful response (optional): ')
    try:
        created=create_api(ROOT,**vars(args))
    except (ValueError,OSError,KeyError,yaml.YAMLError) as exc:parser.exit(1,f'API NOT CREATED: {exc}\n')
    print(f'\nCreated {len(created)} files for {args.name}. All five API environments remain disabled.')
    for p in created:print('  '+p.relative_to(ROOT).as_posix())
    print(f'\nNEXT: edit apis/{args.name}/overlays/dev.yaml with approved DEV values.')
    print(f'Then run: bash scripts/build.sh {args.name} dev build/{args.name}/dev')
    print('Read docs/ADD_AN_API.md for the review and deployment checklist. Do not rerun the starter to update an existing API.')
    if args.tier=='external':print('External API: replace the documentation-only IP allow list and review the OpenAPI contract before enablement.')

if __name__=='__main__':main()
