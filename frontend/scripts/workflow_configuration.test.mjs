import test from "node:test";
import assert from "node:assert/strict";
import {
  blankWorkflow,
  workflowForm,
  workflowPayload,
  selectionGuard,
  dependencyError,
} from "../src/workflowConfiguration.js";
test("persisted calendar windows and SLA restore without inventing recurrence", () => {
  const form = workflowForm({
    id: "w",
    name: "Daily",
    schedule: { timezone: "Asia/Kolkata", weekdays: [0, 2] },
    expected_window_start: "08:00",
    expected_window_end: "10:00",
    sla_seconds: 900,
  });
  assert.equal(form.timezone, "Asia/Kolkata");
  assert.deepEqual(form.weekdays, [0, 2]);
  assert.equal(form.sla_seconds, 900);
  const payload = workflowPayload(form, "a", false);
  assert.equal(payload.expected_window_start, "08:00");
  assert.equal(payload.sla_seconds, 900);
  assert.equal("organization_id" in payload, false);
  assert.equal("frequency_seconds" in payload, false);
  assert.equal("active" in payload, false);
});
test("new workflows use explicit organization, paired optional windows and no invented activation", () => {
  const payload = workflowPayload(
    { ...blankWorkflow(), name: "  Draft  " },
    "a",
    true,
  );
  assert.equal(payload.name, "Draft");
  assert.equal(payload.organization_id, "a");
  assert.equal(payload.sla_seconds, null);
  assert.equal(payload.expected_window_start, null);
  assert.throws(
    () =>
      workflowPayload(
        { ...blankWorkflow(), name: "x", expected_window_start: "09:00" },
        "a",
        true,
      ),
    /Both/,
  );
  assert.throws(
    () =>
      workflowPayload(
        { ...blankWorkflow(), name: "x", weekdays: [] },
        "a",
        true,
      ),
    /weekday/,
  );
});
test("late customer/workflow responses cannot pass the current selection generation", async () => {
  const guard = selectionGuard();
  let release;
  const first = guard.next();
  let shown = "b";
  const pending = new Promise((resolve) => {
    release = resolve;
  }).then(() => {
    if (guard.current(first)) shown = "a";
  });
  guard.next();
  release();
  await pending;
  assert.equal(shown, "b");
});
test("dependency validation excludes self and duplicates and delegates cycle authority", () => {
  const rows = [{ predecessor_job_id: "a", successor_job_id: "b" }];
  assert.match(dependencyError(rows, "a", "a"), /itself/);
  assert.match(dependencyError(rows, "a", "b"), /already/);
  assert.equal(dependencyError(rows, "b", "a"), null);
});

test("timezone validation identifies the field without relaxing backend redaction", () => {
  assert.throws(
    () =>
      workflowPayload(
        { ...blankWorkflow(), name: "x", timezone: "Not/AZone" },
        "a",
        true,
      ),
    /Timezone/,
  );
});
