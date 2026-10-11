#!/usr/bin/env python3
"""Real monitoring lifecycle plus UI Test 1 theme/browser acceptance."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
env['OPSCONTROL_UI_THEME_ACCEPTANCE'] = '1'
env.setdefault('OPERATIONAL_EVIDENCE_DIR', '/tmp/opscontrol-ui-evidence')
sys.exit(subprocess.run([sys.executable, str(root / 'scripts/operational-acceptance.py')], cwd=root, env=env).returncode)
