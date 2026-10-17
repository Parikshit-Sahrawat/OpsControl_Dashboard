import test from "node:test";
import assert from "node:assert/strict";
import {
  outcome,
  params,
  nativeType,
  scheduleAuthority,
  reviewActions,
  linkActions,
  requestGeneration,
  time,
  INCIDENT_TRANSITIONS,
  PAGES,
  binding,
  errorMessage,
} from "../src/pipelines/contracts.js";
test("six pages and seven existing incident states", () => {
  assert.equal(Object.keys(PAGES).length, 6);
  assert.equal(Object.keys(INCIDENT_TRANSITIONS).length, 7);
});
test("pending retry remains nonterminal despite failed attempt", () =>
  assert.equal(
    outcome({
      pentaho_resource_id: "r",
      pentaho_lifecycle: "WAITING_FOR_RETRY",
      pentaho_outcome: "FAILED",
      status: "FAILED",
    }),
    "WAITING_FOR_RETRY",
  ));
test("scheduler or process success cannot imply verified native success", () =>
  assert.equal(
    outcome({ pentaho_resource_id: "r", status: "SUCCESS" }),
    "UNKNOWN",
  ));
test("scheduler retry and manual recovery preserve original failure", () => {
  const original = { pentaho_resource_id: "r", pentaho_outcome: "FAILED" };
  assert.equal(
    outcome({
      pentaho_resource_id: "r",
      pentaho_outcome: "SUCCESS_AFTER_RETRY",
    }),
    "SUCCESS_AFTER_RETRY",
  );
  assert.equal(outcome(original), "FAILED");
});
test("explicit customer scope never expands to ALL", () =>
  assert.equal(
    params(["a", "b", "a"], "TEST", { offset: 20, search: "a & b" }),
    "organization_id=a&organization_id=b&environment=TEST&offset=20&search=a+%26+b",
  ));
test("old success or failure is invalidated on customer switch", async () => {
  const g = requestGeneration(),
    a = g.next();
  g.invalidate();
  const b = g.next();
  await Promise.resolve();
  assert.equal(g.accepts(a), false);
  assert.equal(g.accepts(b), true);
  g.invalidate();
  assert.equal(g.accepts(b), false);
});
test("native workload classifications remain distinct", () => {
  assert.equal(nativeType({ configuration: { platform: "AIRFLOW" } }), "DAG");
  assert.equal(nativeType({ configuration: { platform: "SSIS" } }), "Package");
  assert.equal(
    nativeType({
      configuration: { platform: "PENTAHO", workload_kind: "TRANSFORMATION" },
    }),
    "TRANSFORMATION",
  );
});
test("persisted schedule authority and incomplete coverage stay explicit", () => {
  for (const mode of ["MONITORING_EXPECTATION", "VERIFIED_SCHEDULER"])
    assert.equal(
      scheduleAuthority({ pentaho_authority: { selection: { mode } } }).mode,
      mode,
    );
  assert.equal(scheduleAuthority({ status: "INCOMPLETE" }).mode, "UNKNOWN");
});
test("review actions require category and verified completion", () => {
  assert.deepEqual(reviewActions({ status: "ACCEPTED" }), []);
  assert.deepEqual(
    reviewActions({ status: "OPEN", category: "AMBIGUOUS_IDENTITY" }),
    ["DEFER", "REJECT_CLAIM"],
  );
  assert.ok(
    !reviewActions({ status: "OPEN", category: "EXECUTION_OUTCOME" }).includes(
      "ACCEPT_VERIFIED_CLAIM",
    ),
  );
  assert.ok(
    reviewActions({
      status: "OPEN",
      category: "EXECUTION_OUTCOME",
      context: {
        identity: { completion_evidence: true },
        verification: { claims: ["EXECUTION_OUTCOME"] },
      },
    }).includes("ACCEPT_VERIFIED_CLAIM"),
  );
  assert.ok(
    reviewActions({ status: "OPEN", category: "LEGACY_ADOPTION" }).includes(
      "ADOPT_LEGACY",
    ),
  );
});
test("independent recovery confirmation and confirmed-only reversal", () => {
  assert.deepEqual(
    linkActions({ status: "PROPOSED", proposed_by: "a" }, "a"),
    [],
  );
  assert.deepEqual(linkActions({ status: "PROPOSED", proposed_by: "a" }, "b"), [
    "CONFIRM",
  ]);
  assert.deepEqual(linkActions({ status: "CONFIRMED" }, "b"), ["REVERSE"]);
  assert.deepEqual(linkActions({ status: "REVERSED" }, "b"), []);
});
test("timestamps use explicit UTC", () => {
  assert.equal(
    time("2026-10-16T10:00:00+02:00"),
    "2026-10-16 08:00:00.000 UTC",
  );
  assert.equal(time(null), "Not observed");
  assert.equal(time("invalid"), "Invalid timestamp");
});
test("capabilities follow bound methods only", () => {
  const result = binding(
    { id: "r" },
    {
      jobs: [{ id: "j", resource_id: "r" }],
      associations: [{ job_id: "j", method_id: "m" }],
      methods: [
        { id: "m", capability_id: "c" },
        { id: "unrelated", capability_id: "x" },
      ],
      capabilities: [{ id: "c" }, { id: "x" }],
    },
  );
  assert.deepEqual(result.capabilities, [{ id: "c" }]);
});
test("revision and authorization errors are explicit", () => {
  assert.match(errorMessage({ status: 409, message: "revision" }), /Refresh/);
  assert.match(errorMessage({ status: 403 }), /Permission denied/);
});
