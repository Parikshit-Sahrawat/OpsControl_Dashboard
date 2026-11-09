#!/usr/bin/env python3
import os,sys
args=sys.argv[1:]
# Environment-only storage overlay for this task's ephemeral ETL fixture.
if args and args[0]=='run' and '--name'in args:
 name=args[args.index('--name')+1]
 if name.startswith('opscontrol-etl-') and args[-1]=='postgres:17-alpine' and '--tmpfs'not in args:args[1:1]=['--tmpfs','/var/lib/postgresql/data']
real=open('/tmp/ci004-real-docker-path').read().strip();os.execv(real,[real,*args])
