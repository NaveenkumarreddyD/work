#!/usr/bin/env python3
"""Publish redacted JSON evidence; never publish raw live state/diffs or stderr."""
import json
from pathlib import Path
import re
import shutil
import sys
SECRET=re.compile(r'secret|password|token|private.?key|authorization|cookie|headers|certificate',re.I)
def redact(value):
    if isinstance(value,dict):return {k:('[REDACTED]' if SECRET.search(str(k)) else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    return value

def publish(source,destination):
    source=Path(source);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*.json'):
        try:data=json.loads(p.read_text())
        except ValueError:continue # A partial error response must not expose raw text.
        (destination/p.name).write_text(json.dumps(redact(data),indent=2,sort_keys=True)+'\n')
    for p in source.glob('*-status.txt'):shutil.copyfile(p,destination/p.name)
    p=source/'http-tests.txt'
    if p.exists():shutil.copyfile(p,destination/p.name)
if __name__=='__main__':
    if len(sys.argv)!=3:sys.exit('usage: evidence.py PRIVATE_DIRECTORY PUBLISHED_DIRECTORY')
    publish(*sys.argv[1:])
