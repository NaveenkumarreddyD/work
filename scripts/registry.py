#!/usr/bin/env python3
"""First-seen immutable reference/package binding on trusted durable storage.

Jenkins must hold the global release-registry lock. This is not a GitLab tag
protection substitute or a cryptographic signature. Restrict registry writes to
trusted jobs and retain it outside ephemeral workspaces.
"""
import json
import os
from pathlib import Path
import re
import sys
from release import sha, TAG
from validate import identifier

def register(registry, package):
    registry=Path(registry);package=Path(package)
    if not registry.is_dir() or registry.is_symlink(): raise ValueError('provision trusted durable registry first')
    m=json.loads((package/'manifest.json').read_text());identifier(m['api'])
    if not (TAG.fullmatch(m['tag']) or re.fullmatch('dev-[a-f0-9]{40}',m['tag'])): raise ValueError('invalid reference')
    for key in ('commit','tag_object'):
        if not re.fullmatch('[a-f0-9]{40}',m[key]): raise ValueError('invalid Git identity')
    # Global tag binding protects even when different APIs first deploy in different builds.
    entries=[(m['tag']+'.json', {'commit':m['commit'],'tag_object':m['tag_object']}),
             (m['tag']+'--'+m['api']+'.json', {'manifest_sha256':sha(package/'manifest.json')})]
    for name, binding in entries:
        path=registry/name
        if path.is_symlink(): raise ValueError('registry symlink rejected')
        data=(json.dumps(binding,sort_keys=True)+'\n').encode()
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o440)
        except FileExistsError:
            if path.read_bytes()!=data: raise ValueError('immutable release ref/package changed; issue a new tag')
        else:
            with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    print('Immutable reference/package binding verified')

if __name__=='__main__':
    try:
        if len(sys.argv)!=3: raise ValueError('usage: registry.py REGISTRY PACKAGE')
        register(*sys.argv[1:])
    except (ValueError,KeyError,OSError) as e:sys.exit(str(e))
