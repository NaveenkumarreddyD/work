#!/usr/bin/env python3
import pathlib,re,sys
text=pathlib.Path(sys.argv[1]).read_text()
found=re.findall(r'Summary:\s*Created:\s*(\d+)\s*Updated:\s*(\d+)\s*Deleted:\s*(\d+)',text,re.I)
if not found or tuple(map(int,found[-1])) != (0,0,0):
    sys.exit('Post-sync diff not empty or missing: investigate before promotion')
print('Post-sync state matches managed desired state')
