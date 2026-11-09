"""Standard-library contract validation for authority registration, not certification."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GATES = {"CHK-001": "FAIL", "CHK-002": "BLOCKED", "SECURITY": "BLOCKED", "PRODUCTION_RELEASE": "NO-GO", "FORMAL_OWNER_UAT": "PENDING", "DEVELOPMENT_CLOSURE": "NOT COMPLETE"}
FIELDS = {"authority_id", "decision_version", "approval_status", "supersession_status", "original_source_and_provenance", "applicable_product_journey_ids", "applicable_closure_step_ids", "module_and_capability_ownership", "implementation_status", "source_code_references", "automated_test_references_and_outcomes", "evidence_artifacts_and_commit_sha", "gaps_blockers_dependencies", "owner_uat_acceptance", "release_eligibility_and_gates"}


def validate(record, reconciliation):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(record["authority_id"] == "AUTH-694" and record["decision_version"] == 1, "Authority/version mismatch")
    require(record["selected_option"] == "A" and record["round"] == 110 and record["decision_status"] == "APPROVED", "Owner selection/round/approval changed")
    require(record["approval_source"] == "PRODUCT_OWNER_CHATGPT_CONVERSATION", "Approval provenance changed")
    require(record["repository_source_artifact"] == "SOURCE_NOT_RECOVERED", "Original artifact cannot be manufactured")
    require(all(record["original_source"][key] is None for key in ("repository_url", "approval_timestamp", "signature")), "Fabricated original provenance")
    require(record["repository_implementation_status"] == "NOT_VERIFIED" and record["certification_status"] == "NOT_CERTIFIED" and record["formal_uat_acceptance"] == "PENDING", "Approval cannot promote implementation/certification/UAT")
    require(record["gates"] == GATES and reconciliation["independent_gates"] == GATES, "Gate promotion forbidden")
    require({r["authority_id"]: r["selected_option"] for r in record["preserved_decisions"]} == {"AUTH-491": "B", "AUTH-495": "C"}, "Historical selections changed")
    require(set(record["closure_evidence_rule"]["distinct_states"]) == {"ASSUMED_EXTERNAL_CLOSURE", "PROVIDER_VERIFIED_CLOSURE"}, "Closure evidence types collapsed")
    journeys = reconciliation["journeys"]
    require([j["journey_id"] for j in journeys] == [f"{i:02d}" for i in range(1, 34)], "Missing/duplicate journey slot")
    require(sum(j["scope_status"] == "INCLUDED" for j in journeys) == 31, "Included journey count changed")
    require(journeys[19]["scope_status"] == "EXCLUDED" and journeys[31]["scope_status"] == "SKIPPED", "Scope exclusion changed")
    for j in journeys:
        if j["journey_id"] not in {"20", "32", "33"}:
            require(j["description"] == j["definition_status"] == "SOURCE_NOT_RECOVERED", "Invented original journey definition")
    steps = reconciliation["closure_steps"]
    require([s["step_id"] for s in steps] == list(range(1, 15)), "Closure steps reordered/missing")
    require([s["checklist_status"] for s in steps] == ["PARTIAL"] + ["PENDING"] * 11 + ["BLOCKED", "BLOCKED"], "Checklist advancement not authorized by registration")
    require(set(record["required_traceability_fields"]) == FIELDS, "Traceability contract missing fields")
    for row in journeys + steps:
        require(FIELDS <= row.keys(), "Missing per-requirement traceability fields")
        require(row["authority_id"] == "AUTH-694" and row["decision_version"] == 1, "Row authority mismatch")
        require(row["implementation_status"] == "NOT_VERIFIED", "Registration is not implementation evidence")
        require(row["owner_uat_acceptance"]["status"] == "PENDING", "UAT approval fabricated")
        require(row["release_eligibility_and_gates"]["gates"] == GATES and row["release_eligibility_and_gates"]["eligibility"] == "BLOCKED", "Row gate promotion")
    return {"status": "PASS", "authority": "AUTH-694", "journey_slots": 33, "included_journeys": 31, "unrecovered_numbered_definitions": 30, "ordered_closure_steps": 14, "note": "Documentation contract validation only; no implementation/provider/UAT/release certification"}


def load():
    return json.loads((ROOT / "AUTH-694.v1.json").read_text()), json.loads((ROOT / "AUTH-694_RECONCILIATION.v1.json").read_text())


if __name__ == "__main__":
    print(json.dumps(validate(*load()), indent=2))
