"""Developer-only inventory update. CI runs policy.py, never this generator."""

import json
from pathlib import Path
from policy import ROOT, test_inventory

p = ROOT / ".ci/scope-manifest.json"
old = json.loads(p.read_text()) if p.exists() else {}
rows = test_inventory(ROOT)
for key in rows:
    if key in old.get("tests", {}):
        rows[key] = old["tests"][key]
protected = {
    "backend/tests/test_eks_discovery.py": [
        "test_even_platform_admin_cannot_discover_removed_platform",
        "self.assertFalse(hasattr",
    ],
    "backend/tests/test_kubernetes_cluster_associations.py": [
        "test_legacy_history_identity_revision_and_delete_guards",
        "UPDATE kubernetes_cluster_association_decisions",
    ],
    "backend/tests/test_removed_platform_scope.py": [
        "test_nested_source_template_and_collector_configs_are_rejected"
    ],
    "backend/tests/test_native_incidents_v15.py": [
        "test_service_denies_cross_customer",
        "test_duplicate_worker_lease_performs_no_writes",
    ],
    "backend/scripts/provider_unit_probe.py": [
        "def test_aws",
        "def test_pentaho",
        "Unsafe or invalid provider config accepted",
    ],
}
for key, row in rows.items():
    if key.startswith("backend/tests/test_eks_discovery.py::") or key.startswith(
        "backend/tests/test_removed_platform_scope.py::"
    ):
        row.update(
            classification=(
                "INCLUDED_POSITIVE"
                if "test_supported_source_inputs_preserved" in key
                else "EXCLUDED_NEGATIVE"
            ),
            reason="Reviewed supported input preservation or excluded capability denial",
        )
    elif key.startswith("backend/tests/test_kubernetes_cluster_associations.py::"):
        row.update(
            classification="LEGACY_PRESERVATION",
            reason="Historical scope and append-only preservation; never skip",
        )
p.write_text(
    json.dumps(
        {
            "schema": 1,
            "policy": "Unknown tests run broad existing suites. No test retirement authorized by a filename. Source reviews required before changing classifications.",
            "authority": "Owner approved CI001 implementation and all-PR gates; b8c1615340828d1d3031c635fb319565dd9f222a",
            "protected_assertions": protected,
            "tests": rows,
        },
        indent=2,
    )
    + "\n"
)
