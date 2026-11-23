#!/usr/bin/env python3
"""Release integrity and JSON diff checks. Does not generate Kong entities."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate import ROOT, ENVS, api_directory, contract, https, identifier, load, settings, validate_state

TAG=re.compile(r'kong-v\d+\.\d+\.\d+(?:-rc\d+)?\Z')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_file(root, relative):
    if not isinstance(relative,str): raise ValueError('package path must be string')
    p=PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or '\\' in relative or str(p)!=relative: raise ValueError('unsafe package path')
    result=root
    for part in p.parts:
        result=result/part
        if result.is_symlink(): raise ValueError('package symlink rejected')
    if not result.is_file() or result.stat().st_size>10_000_000: raise ValueError('missing or excessive package file')
    return result

def verify_package(package, api, env, cp, address):
    package=Path(package)
    if package.is_symlink() or not package.is_dir(): raise ValueError('package directory/symlink rejected')
    identifier(api)
    if env not in ENVS: raise ValueError('invalid environment')
    m=json.loads(safe_file(package,'manifest.json').read_text())
    if set(m)!={'schema','api','tier','tag','tag_object','commit','deck','files','environments'}: raise ValueError('invalid manifest keys')
    if m['schema']!=1 or m['api']!=api or m['tier'] not in ('internal','external') or m['deck']!='1.70.0': raise ValueError('package identity/version mismatch')
    if not (TAG.fullmatch(m['tag']) or m['tag']=='dev-'+m['commit']) or not re.fullmatch('[a-f0-9]{40}',m['commit']) or not re.fullmatch('[a-f0-9]{40}',m['tag_object']): raise ValueError('invalid release identity')
    if not isinstance(m['files'],dict) or not m['files']: raise ValueError('missing package files')
    if not isinstance(m['environments'],dict) or set(m['environments'])-set(ENVS): raise ValueError('invalid environment list')
    required={'tests.json'}
    for name,entry in m['environments'].items():
        if set(entry)!={'enabled','control_plane','konnect_addr','gateway_url','state'}: raise ValueError('invalid target entry')
        if type(entry['enabled']) is not bool or entry['state']!=f'{name}/state.yaml': raise ValueError('invalid target state')
        https(entry['konnect_addr'],'Konnect target');https(entry['gateway_url'],'gateway target')
        required.add(entry['state'])
    if set(m['files'])!=required: raise ValueError('package file list mismatch')
    for name,digest in m['files'].items():
        if not re.fullmatch('[a-f0-9]{64}',str(digest)) or sha(safe_file(package,name))!=digest: raise ValueError(f'checksum mismatch: {name}')
    actual=set()
    for p in package.rglob('*'):
        if p.is_symlink(): raise ValueError('package symlink rejected')
        if p.is_file(): actual.add(p.relative_to(package).as_posix())
    if actual!=set(m['files'])|{'manifest.json'}: raise ValueError('unexpected package files')
    if env not in m['environments']: raise ValueError('environment absent from package')
    if m['tag'].startswith('dev-') and env!='dev': raise ValueError('DEV package cannot target higher environments')
    target=m['environments'][env]
    if target['enabled'] is not True: raise ValueError('target/API disabled in this immutable release')
    if target['control_plane']!=cp or target['konnect_addr']!=address: raise ValueError('expected target does not match release target')
    return m

def check_diff(report, allow_deletions):
    if not isinstance(report,dict) or report.get('errors'): raise ValueError('decK diff errors')
    summary=report.get('summary',{})
    if set(summary)!={'creating','updating','deleting','total'} or any(type(v)is not int or v<0 for v in summary.values()): raise ValueError('invalid diff summary')
    if summary['total']!=sum(summary[k] for k in ('creating','updating','deleting')): raise ValueError('invalid diff totals')
    changes=report.get('changes',{})
    if set(changes)!={'creating','updating','deleting'} or any(not isinstance(v,list) for v in changes.values()): raise ValueError('invalid diff changes')
    if any(len(changes[k])!=summary[k] for k in changes): raise ValueError('diff count mismatch')
    if summary['deleting'] and not allow_deletions: raise ValueError('deletion requires explicit authorization and snapshot')
    return summary

def compare_plans(approved,current):
    if approved!=current: raise ValueError('plan changed since approval; review and approve a new plan')

def make_manifest(root,package,api,tag):
    git=lambda *args:subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    commit=git('rev-parse','HEAD')
    if tag=='dev-'+commit:
        tag_object=commit
    else:
        if not TAG.fullmatch(tag): raise ValueError('release tag must match kong-vMAJOR.MINOR.PATCH')
        if git('cat-file','-t',f'refs/tags/{tag}')!='tag': raise ValueError('annotated tag required')
        if git('rev-parse',f'refs/tags/{tag}^{{commit}}')!=commit: raise ValueError('checkout release tag before building')
        tag_object=git('rev-parse',f'refs/tags/{tag}')
        if os.environ.get('REQUIRE_SIGNED_TAG')=='true':subprocess.run(['git','verify-tag',tag],cwd=root,check=True)
    subprocess.run(['git','merge-base','--is-ancestor',commit,'refs/remotes/origin/main'],cwd=root,check=True)
    if git('status','--porcelain','--untracked-files=no'): raise ValueError('release build requires clean tracked files')
    meta=load(api_directory(root,api)/'metadata.yaml')
    manifest={'schema':1,'api':api,'tier':meta['tier'],'tag':tag,'tag_object':tag_object,'commit':commit,'deck':'1.70.0','files':{},'environments':{}}
    tests=load(api_directory(root,api)/'tests.yaml')['tests']
    (package/'tests.json').write_text(json.dumps(tests,indent=2)+'\n')
    manifest['files']['tests.json']=sha(package/'tests.json')
    spec=load(api_directory(root,api)/'openapi.yaml')
    for env in ENVS:
        m,t,v=settings(root,api,env)
        enabled=t['enabled'] and v['enabled']
        if enabled:
            settings(root,api,env,True)
            state=load(package/env/'state.yaml')
            validate_state(state,api,m['tier'],env);contract(state,spec,tests)
        relative=f'{env}/state.yaml'
        manifest['files'][relative]=sha(package/relative)
        manifest['environments'][env]={'enabled':enabled,'control_plane':t['control_plane'],'konnect_addr':t['konnect_addr'],'gateway_url':v['gateway_url'],'state':relative}
    (package/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(f'Release package created: {tag}, {api}; disabled environments cannot deploy')


def approval_binding(package,evidence,api,env,cp,address):
    m=verify_package(package,api,env,cp,address)
    if sha(evidence/'state.yaml')!=m['files'][f'{env}/state.yaml']:
        raise ValueError('staged state checksum changed')
    return {'manifest_sha256':sha(package/'manifest.json'),'plan_sha256':sha(evidence/'plan.json'),'state_sha256':sha(evidence/'state.yaml'),'api':api,'environment':env,'control_plane':cp,'konnect_addr':address}

def evidence_action(command,package,evidence,api,env,cp,address,reviewer=None,ticket=None):
    m=verify_package(package,api,env,cp,address)
    if command=='stage':
        if evidence.exists(): raise ValueError('use a new evidence directory for every plan')
        evidence.mkdir(parents=True,mode=0o700)
        shutil.copyfile(package/env/'state.yaml',evidence/'state.yaml')
        if sha(evidence/'state.yaml')!=m['files'][f'{env}/state.yaml']: raise ValueError('staged checksum mismatch')
        return
    binding=approval_binding(package,evidence,api,env,cp,address)
    if command=='approve':
        if not reviewer or not ticket: raise ValueError('approver and change ticket required')
        check_diff(json.loads((evidence/'plan.json').read_text()),True)
        binding.update(approver=reviewer,change_ticket=ticket)
        (evidence/'approval.json').write_text(json.dumps(binding,sort_keys=True,indent=2)+'\n')
    else:
        approved=json.loads((evidence/'approval.json').read_text())
        if not approved.get('approver') or not approved.get('change_ticket'): raise ValueError('approval missing identity/ticket')
        if {k:approved.get(k) for k in binding}!=binding: raise ValueError('approval does not match package/plan/state/target')

PREDECESSOR={'uat':'dev','training':'dev','preprod':'uat','prod':'preprod'}

def check_identity(package, ref, commit, tag_object):
    m=json.loads(safe_file(Path(package),'manifest.json').read_text())
    if (m.get('tag'),m.get('commit'),m.get('tag_object'))!=(ref,commit,tag_object):
        raise ValueError('release identity differs from fetched immutable reference')

def check_receipt(manifest, env, receipt, action, package):
    if env not in ENVS or action not in ('DEPLOY','ROLLBACK'): raise ValueError('invalid delivery request')
    if env!='dev' and manifest['tag'].startswith('dev-'): raise ValueError('DEV package cannot promote')
    if receipt.get('schema')!=1 or receipt.get('status')!='success' or receipt.get('api')!=manifest['api']:
        raise ValueError('successful receipt for this API required')
    if receipt.get('commit')!=manifest['commit']: raise ValueError('predecessor commit differs')
    expected=env if action=='ROLLBACK' else PREDECESSOR.get(env)
    if receipt.get('environment')!=expected: raise ValueError('wrong predecessor/destination environment')
    if action=='ROLLBACK':
        target=manifest['environments'][env]
        if receipt.get('manifest_sha256')!=sha(Path(package)/'manifest.json'):
            raise ValueError('rollback package was not the known-good package')
        if (receipt.get('control_plane'),receipt.get('konnect_addr'))!=(target['control_plane'],target['konnect_addr']):
            raise ValueError('rollback target differs from known-good destination')
    elif expected!='dev' and receipt.get('manifest_sha256')!=sha(Path(package)/'manifest.json'):
        raise ValueError('higher-environment package differs from predecessor')

def write_receipt(package, api, env, cp, address, evidence, build_url):
    m=verify_package(package,api,env,cp,address)
    if (evidence/'apply-status.txt').read_text().strip()!='exit_code=0': raise ValueError('apply did not succeed')
    check_diff(json.loads((evidence/'postdiff.json').read_text()),True)
    if json.loads((evidence/'postdiff.json').read_text())['summary']['total']: raise ValueError('post-sync drift')
    if 'Passed ' not in (evidence/'http-tests.txt').read_text(): raise ValueError('smoke evidence missing')
    r={'schema':1,'status':'success','api':api,'environment':env,'tag':m['tag'],'commit':m['commit'],
       'manifest_sha256':sha(Path(package)/'manifest.json'),'control_plane':cp,'konnect_addr':address,'build_url':build_url,'package_build':os.environ.get('PACKAGE_BUILD','')}
    (evidence/'receipt.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    make=sub.add_parser('manifest');make.add_argument('package',type=Path);make.add_argument('api');make.add_argument('tag')
    verify=sub.add_parser('verify');verify.add_argument('package',type=Path);verify.add_argument('api');verify.add_argument('env');verify.add_argument('cp');verify.add_argument('address')
    diff=sub.add_parser('diff');diff.add_argument('file',type=Path);diff.add_argument('--allow-deletions',action='store_true');diff.add_argument('--empty',action='store_true')
    compare=sub.add_parser('compare');compare.add_argument('approved',type=Path);compare.add_argument('current',type=Path)
    for command in ('stage','approve','binding'):
        c=sub.add_parser(command);c.add_argument('package',type=Path);c.add_argument('evidence',type=Path);c.add_argument('api');c.add_argument('env');c.add_argument('cp');c.add_argument('address')
        if command=='approve':c.add_argument('reviewer');c.add_argument('ticket')
    identity=sub.add_parser('identity');identity.add_argument('package',type=Path);identity.add_argument('ref');identity.add_argument('commit');identity.add_argument('tag_object')
    receipt=sub.add_parser('receipt-check');receipt.add_argument('package',type=Path);receipt.add_argument('env');receipt.add_argument('receipt',type=Path);receipt.add_argument('action')
    record=sub.add_parser('record');record.add_argument('package',type=Path);record.add_argument('api');record.add_argument('env');record.add_argument('cp');record.add_argument('address');record.add_argument('evidence',type=Path);record.add_argument('build_url')
    a=p.parse_args()
    try:
        if a.cmd=='identity':check_identity(a.package,a.ref,a.commit,a.tag_object)
        elif a.cmd=='receipt-check':check_receipt(json.loads((a.package/'manifest.json').read_text()),a.env,json.loads(a.receipt.read_text()),a.action,a.package)
        elif a.cmd=='record':write_receipt(a.package,a.api,a.env,a.cp,a.address,a.evidence,a.build_url)
        elif a.cmd in ('stage','approve','binding'):
            evidence_action(a.cmd,a.package,a.evidence,a.api,a.env,a.cp,a.address,getattr(a,'reviewer',None),getattr(a,'ticket',None))
        elif a.cmd=='manifest':make_manifest(ROOT,a.package,a.api,a.tag)
        elif a.cmd=='verify':
            m=verify_package(a.package,a.api,a.env,a.cp,a.address)
            validate_state(load(a.package/a.env/'state.yaml'),a.api,m['tier'],a.env)
            print(json.dumps(m['environments'][a.env]))
        elif a.cmd=='diff':
            s=check_diff(json.loads(a.file.read_text()),a.allow_deletions)
            if a.empty and s['total']:raise ValueError('post-sync state differs from desired state')
            print(json.dumps(s))
        else:compare_plans(json.loads(a.approved.read_text()),json.loads(a.current.read_text()))
    except (ValueError,KeyError,TypeError,OSError,subprocess.CalledProcessError) as exc:sys.exit(f'RELEASE CHECK FAILED: {exc}')

if __name__=='__main__':main()
