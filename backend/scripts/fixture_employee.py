"""Current employee contract for owned test/demo HTTP fixtures only."""
import uuid
from app.core.config import settings

def with_department(body,create_department):
    if settings.environment not in ('test','demo'):
        raise RuntimeError('Fixture employee provisioning is limited to owned test/demo environments')
    name='Controlled Test Team '+uuid.uuid4().hex[:8]
    department=create_department({'name':name,'code':'UT-'+uuid.uuid4().hex[:12],'active':True})
    return {**body,'department_id':department['id']}
