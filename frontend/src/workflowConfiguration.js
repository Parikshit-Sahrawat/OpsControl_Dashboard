export const blankWorkflow = () => ({
  name: "",
  environment: "PROD",
  timezone: "UTC",
  weekdays: [0, 1, 2, 3, 4, 5, 6],
  expected_window_start: "",
  expected_window_end: "",
  expected_duration_seconds: "",
  sla_seconds: "",
});
export function workflowForm(row) {
  return {
    ...blankWorkflow(),
    ...row,
    timezone: row.schedule?.timezone || "UTC",
    weekdays: row.schedule?.weekdays || [],
    expected_window_start: row.expected_window_start || "",
    expected_window_end: row.expected_window_end || "",
    sla_seconds: row.sla_seconds ?? "",
    expected_duration_seconds: row.expected_duration_seconds ?? "",
  };
}
export function workflowPayload(form, organization, creating) {
  if (!form.name.trim()) throw Error("Workflow name is required");
  try {
    new Intl.DateTimeFormat("en", { timeZone: form.timezone });
  } catch {
    throw Error("Timezone must be a valid IANA timezone");
  }
  if (Boolean(form.expected_window_start) !== Boolean(form.expected_window_end))
    throw Error("Both expected window endpoints are required");
  if (!form.weekdays.length) throw Error("Select at least one weekday");
  return {
    name: form.name.trim(),
    environment: form.environment,
    timezone: form.timezone,
    weekdays: form.weekdays,
    expected_window_start: form.expected_window_start || null,
    expected_window_end: form.expected_window_end || null,
    sla_seconds: form.sla_seconds === "" ? null : Number(form.sla_seconds),
    expected_duration_seconds:
      form.expected_duration_seconds === ""
        ? null
        : Number(form.expected_duration_seconds),
    ...(creating ? { organization_id: organization } : {}),
  };
}
// One generation per tenant/workflow selection; edits are never hydrated by polling.
export function selectionGuard() {
  let version = 0;
  return {
    next() {
      return ++version;
    },
    current(ticket) {
      return ticket === version;
    },
    capture() {
      return version;
    },
  };
}
export function dependencyError(edges, predecessor, successor) {
  if (!predecessor || !successor) return "Select both Jobs";
  if (predecessor === successor) return "A Job cannot depend on itself";
  if (
    edges.some(
      (edge) =>
        edge.predecessor_job_id === predecessor &&
        edge.successor_job_id === successor,
    )
  )
    return "Dependency already exists";
  return null; // The transactional backend is the authority for graph cycles.
}
