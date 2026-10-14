#!/usr/bin/env python3
"""Sprint 4 virtual lab: reuse the disposable ETL/host stack, add real HTTP and NOC gates."""
import os, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
env=os.environ.copy()
env['OPSCONTROL_SPRINT4_ACCEPTANCE']='1'
env.setdefault('OPERATIONAL_EVIDENCE_DIR',str(root/'docs/screenshots/operational'))
env['ETL_EVIDENCE_DIR']=str(Path(env['OPERATIONAL_EVIDENCE_DIR'])/'etl')
env.setdefault('PLAYWRIGHT_MODULE','/workspace/.golden-tools/node_modules/playwright/index.mjs')
if Path('/usr/bin/chromium').is_file():env.setdefault('PLAYWRIGHT_CHROMIUM_EXECUTABLE','/usr/bin/chromium')
sys.exit(subprocess.run([str(root/'backend/.venv/bin/python'),str(root/'scripts/etl-acceptance.py')],cwd=root,env=env).returncode)
