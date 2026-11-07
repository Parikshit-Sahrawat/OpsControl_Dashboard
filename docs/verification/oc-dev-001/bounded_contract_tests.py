import sys,os,json,socket,platform,struct,subprocess,unittest
from unittest.mock import patch
from pathlib import Path
from sqlalchemy.engine import Engine
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'backend'));os.chdir(root);os.environ['DATABASE_URL']='postgresql+psycopg://offline:offline@127.0.0.1:1/offline';os.environ['ENV']='test';os.environ['ENVIRONMENT']='test';blocked=[]
def deny(*a,**k):blocked.append('forbidden IO');raise AssertionError('OC-DEV-001 bounded tests forbid network/DB/process IO')
targets=['tests.test_registry_contracts','tests.test_schema_contract','tests.test_api_monitoring_config','tests.test_access_control','tests.test_notification_transport','tests.test_condition_refresh','tests.test_pentaho_surface_contracts','tests.test_pentaho_carte_compat']
with patch.object(platform,'architecture',return_value=(str(struct.calcsize('P')*8)+'bit','')),patch.object(Engine,'connect',deny),patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny),patch.object(socket,'getaddrinfo',deny),patch.object(subprocess,'Popen',deny):
 suite=unittest.defaultTestLoader.loadTestsFromNames(targets);result=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'forbidden_io_attempts':len(blocked),'targets':targets}));sys.exit(0 if result.wasSuccessful() and not blocked else 1)
