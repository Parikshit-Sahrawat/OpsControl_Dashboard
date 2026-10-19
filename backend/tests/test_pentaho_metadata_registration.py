"""Regression checks for standalone ORM metadata registration.

These checks do not connect to or mutate a database.
"""
import unittest

import app.models  # noqa: F401 - intentionally registers model package
from app.db.session import Base


class PentahoMetadataRegistrationTests(unittest.TestCase):
    def test_canonical_monitoring_resource_is_registered(self):
        self.assertIn("monitoring_resources", Base.metadata.tables)
        self.assertIn("job_order_histories", Base.metadata.tables)

    def test_pentaho_history_columns_and_scoped_fk_resolve(self):
        history = Base.metadata.tables["job_order_histories"]
        for name in ("pentaho_customer_id", "pentaho_resource_id", "job_order_id"):
            self.assertIn(name, history.c)
        resource = Base.metadata.tables["monitoring_resources"]
        self.assertIn("job_order_id", resource.c)
        scoped = [
            constraint for constraint in history.foreign_key_constraints
            if constraint.name == "fk_pentaho_history_resource_scope"
        ]
        self.assertEqual(len(scoped), 1)
        self.assertEqual(
            {element.column.table.name for element in scoped[0].elements},
            {"monitoring_resources"},
        )
        self.assertEqual(
            {element.column.name for element in scoped[0].elements},
            {"organization_id", "id", "job_order_id"},
        )


if __name__ == "__main__":
    unittest.main()
