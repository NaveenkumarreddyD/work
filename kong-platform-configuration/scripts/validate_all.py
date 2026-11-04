#!/usr/bin/env python3
"""Validate API declarations, OpenAPI parity, and every environment overlay offline."""
import sys
from pathlib import Path
import yaml
from kong_config import ROOT, ENVS, check

def main():
    errors=[]
    api_dirs=sorted(x for x in (ROOT/'apis').iterdir() if x.is_dir())
    if not api_dirs:
        raise SystemExit('No APIs present')
    names=set(); paths=set()
    for api_dir in api_dirs:
        api=api_dir.name
        try:
            for env in ENVS: check(api,env)
            conf=yaml.safe_load((api_dir/'api.yaml').read_text())
            spec=yaml.safe_load((api_dir/'openapi.yaml').read_text())
            if not isinstance(spec,dict) or not str(spec.get('openapi','')).startswith('3.'):
                raise ValueError('OpenAPI 3.x specification required')
            for route in conf['routes']:
                if route['name'] in names: raise ValueError('Duplicate route name across APIs')
                names.add(route['name'])
                for p in route['paths']:
                    for method in route['methods']:
                        if method.lower() not in spec.get('paths',{}).get(p,{}):
                            raise ValueError(f'Missing OpenAPI operation: {method} {p}')
                    unique_key=(conf['tier'],p)
                    if unique_key in paths: raise ValueError('Duplicate route path across APIs on same tier')
                    paths.add(unique_key)
        except (ValueError,KeyError,TypeError,yaml.YAMLError) as exc:
            errors.append(f'{api}: {exc}')
    if errors:
        for e in errors: print('ERROR:',e,file=sys.stderr)
        sys.exit(1)
    print(f'Validated {len(api_dirs)} API(s) and {len(ENVS)} environment overlays each')

if __name__=='__main__': main()
