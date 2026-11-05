#!/usr/bin/env python3
"""Fail closed on direct push, missing CI or missing reviewed merged PR."""
import sys
from pull_release import SHA, api, check_ci, require

def main(sha):
    require(SHA.fullmatch(sha), 'Invalid main SHA')
    require(api('repos/Parikshit-Sahrawat/OpsControl_Dashboard/branches/main')['commit']['sha'] == sha,
            'Main moved')
    pr = check_ci(sha)
    print(f'PASS: main SHA {sha} from merged reviewed PR #{pr} with required checks')

if __name__ == '__main__':
    main(sys.argv[1])
