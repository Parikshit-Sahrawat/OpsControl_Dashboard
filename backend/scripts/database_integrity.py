"""Read-only streaming fingerprints for populated restore acceptance."""
import hashlib
import re
from sqlalchemy import inspect, text

def fingerprint(connection) -> dict:
    connection.execute(text("SET TIME ZONE 'UTC'"))
    tables = {}
    for name in sorted(inspect(connection).get_table_names(schema='public')):
        quoted = '"' + name.replace('"', '""') + '"'
        digest = hashlib.sha256()
        count = 0
        for value in connection.execution_options(stream_results=True).scalars(text(
            f'SELECT to_jsonb(t)::text FROM public.{quoted} t ORDER BY to_jsonb(t)::text')):
            digest.update(value.encode('utf-8') + b'\n')
            count += 1
        tables[name] = {'rows': count, 'sha256': digest.hexdigest()}
    connection.execution_options(stream_results=False)
    constraints = connection.execute(text("""
        SELECT c.relname, k.conname, k.contype, k.convalidated, pg_get_constraintdef(k.oid)
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
        ORDER BY c.relname, k.conname
    """)).all()
    if any(not row.convalidated for row in constraints):
        raise AssertionError('Unvalidated database constraint')
    # pg_dump/restore reparses CHECK expressions. PostgreSQL can move a
    # varchar[] -> text[] coercion to each array element without changing its
    # meaning. Recognize ONLY these exact approved simple text checks;
    # all other definitions, operators, values and constraint metadata must
    # still compare byte-for-byte. Runtime probes also test rejected values.
    approved = {
        ('user_role_assignments', 'ck_employee_role_effect'): "CHECKeffect=ANYARRAY['ALLOW','DENY']",
        ('monitoring_rule_catalogs', 'ck_monitoring_catalog_kind'): "CHECKkind=ANYARRAY['METRIC','LOG','ALERT']",
        ('operational_incidents', 'ck_incident_condition'): "CHECKcondition_status=ANYARRAY['ACTIVE','RECOVERED']",
        ('operational_incidents', 'ck_incident_status'): "CHECKstatus=ANYARRAY['OPEN','ACKNOWLEDGED','INVESTIGATING','RESOLVED']",
    }
    signatures = []
    for row in constraints:
        item = list(row)
        expected = approved.get((row.relname, row.conname))
        if expected:
            folded = re.sub(r"[()\s]", '', re.sub(r"::(?:character varying|text)(?:\[\])?", '', item[-1]))
            if folded != expected:
                raise AssertionError('Approved CHECK semantics changed: '+row.conname)
            item[-1] = expected
        signatures.append(item)
    return {'tables': tables, 'constraints': signatures}
