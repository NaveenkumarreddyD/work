#!/usr/bin/env python3
"""Find APIs changed in current Git commit; emits one name per line."""
import pathlib, subprocess
root=pathlib.Path(__file__).resolve().parents[1]
try:
    changed=subprocess.check_output(['git','diff','--name-only','HEAD^','HEAD'],cwd=root,text=True).splitlines()
except subprocess.CalledProcessError:
    # First commit or shallow checkout: include all APIs, never bypass validation.
    changed=[str(p.relative_to(root)) for p in (root/'apis').glob('*/api.yaml')]
known={p.name for p in (root/'apis').iterdir() if p.is_dir()}
affected=set()
for path in changed:
    parts=path.split('/')
    if len(parts)>=3 and parts[0]=='apis' and parts[1] in known:
        affected.add(parts[1])
    if len(parts)==4 and parts[:2]==['environments','dev'] and parts[2]=='values':
        api=pathlib.Path(parts[3]).stem
        if api in known: affected.add(api)
    if path.startswith(('scripts/','Jenkinsfile')):
        affected.update(known)
print('\n'.join(sorted(affected)))
