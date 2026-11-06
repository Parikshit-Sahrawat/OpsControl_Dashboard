import { useEffect, useRef, useState } from "react";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
import {
  blankWorkflow,
  workflowForm,
  workflowPayload,
  selectionGuard,
  dependencyError,
} from "../workflowConfiguration";
const root = "/api/v1/etl/workflows";
const blankJob = () => ({
  name: "",
  hostname: "",
  expected_duration_seconds: "",
});
export default function ETLWorkflowConfiguration({
  user,
  organizationId,
  environment = "",
}) {
  const [rows, setRows] = useState([]),
    [selected, setSelected] = useState(""),
    [detail, setDetail] = useState(null),
    [form, setForm] = useState(null),
    [job, setJob] = useState(null),
    [edges, setEdges] = useState([]),
    [predecessor, setPredecessor] = useState(""),
    [successor, setSuccessor] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const guard = useRef(selectionGuard()),
    scope = useRef(organizationId);
  scope.current = organizationId;
  const allowed = hasPermission(user, "etl.configure", organizationId),
    canView = hasPermission(user, "etl.view", organizationId);
  const request = (path, method, payload, signal) =>
    control(path, method, payload, { customerIds: [organizationId], signal });
  useEffect(() => {
    const ticket = guard.current.next(),
      abort = new AbortController();
    setRows([]);
    setSelected("");
    setDetail(null);
    setForm(null);
    setJob(null);
    setEdges([]);
    setError("");
    setNotice("");
    setBusy(false);
    if (!organizationId || !canView) {
      setLoading(false);
      return () => abort.abort();
    }
    setLoading(true);
    control(
      root + "?organization_id=" + encodeURIComponent(organizationId),
      "GET",
      undefined,
      { customerIds: [organizationId], signal: abort.signal },
    )
      .then((data) => {
        if (guard.current.current(ticket)) setRows(data);
      })
      .catch((err) => {
        if (guard.current.current(ticket) && err.name !== "AbortError")
          setError(err.message);
      })
      .finally(() => {
        if (guard.current.current(ticket)) setLoading(false);
      });
    return () => {
      guard.current.next();
      abort.abort();
    };
  }, [organizationId, canView]);
  async function open(id) {
    const ticket = guard.current.next();
    setSelected(id);
    setDetail(null);
    setForm(null);
    setJob(null);
    setError("");
    setNotice("");
    setLoading(true);
    setBusy(false);
    setPredecessor("");
    setSuccessor("");
    try {
      const [data, dependencies] = await Promise.all([
        request(root + "/" + id + "/monitoring"),
        request(root + "/" + id + "/dependencies"),
      ]);
      if (guard.current.current(ticket)) {
        setDetail(data);
        setEdges(dependencies);
      }
    } catch (err) {
      if (guard.current.current(ticket)) setError(err.message);
    } finally {
      if (guard.current.current(ticket)) setLoading(false);
    }
  }
  async function save(operation, after) {
    const tenant = organizationId,
      ticket = guard.current.next();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await operation();
      if (scope.current === tenant && guard.current.current(ticket)) {
        await after(result);
        setNotice(
          "Configuration saved. This does not establish operational health.",
        );
      }
    } catch (err) {
      if (scope.current === tenant && guard.current.current(ticket))
        setError(err.message);
    } finally {
      if (scope.current === tenant && guard.current.current(ticket))
        setBusy(false);
    }
  }
  async function reloadDetails(id) {
    const [data, dependencies] = await Promise.all([
      request(root + "/" + id + "/monitoring"),
      request(root + "/" + id + "/dependencies"),
    ]);
    // The enclosing save generation is checked before invoking this callback;
    // also reject tenant switches while these follow-up reads are outstanding.
    if (scope.current !== data.workflow.organization_id) return;
    setDetail(data);
    setEdges(dependencies);
    setSelected(id);
  }
  function editField(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
  }
  const visible = rows.filter(
    (row) => !environment || row.environment === environment,
  );
  if (!organizationId)
    return (
      <section className="card">
        <h2>ETL Workflows</h2>
        <p>Select one customer to configure Workflows.</p>
      </section>
    );
  if (!canView)
    return (
      <section className="card">
        <h2>ETL Workflows</h2>
        <p>Workflow view permission is required.</p>
      </section>
    );
  return (
    <section className="card" aria-label="ETL Workflow configuration">
      <div className="page-heading">
        <div>
          <h2>ETL Workflows</h2>
          <p>
            Monitoring expectations only. External workloads are never executed
            here.
          </p>
        </div>
        {allowed && (
          <button
            disabled={busy || loading}
            onClick={() => {
              guard.current.next();
              setForm(blankWorkflow());
              setJob(null);
              setDetail(null);
              setSelected("");
              setError("");
            }}
          >
            Create Workflow
          </button>
        )}
      </div>
      {loading && <p role="status">Loading Workflow configuration…</p>}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <div className="table-wrap">
        <table>
          <caption>Workflows in the selected customer and environment</caption>
          <thead>
            <tr>
              <th>Name</th>
              <th>Environment</th>
              <th>Saved configuration</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.environment}</td>
                <td>{row.active ? "Enabled setting" : "Disabled setting"}</td>
                <td>
                  <button
                    disabled={busy || loading}
                    onClick={() => open(row.id)}
                  >
                    View {row.name}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!loading && !visible.length && <p>No Workflows match this selection.</p>}
      {form && (
        <form
          aria-label="Workflow editor"
          onSubmit={(event) => {
            event.preventDefault();
            let payload;
            try {
              payload = workflowPayload(form, organizationId, !selected);
            } catch (err) {
              setError(err.message);
              return;
            }
            save(
              () =>
                request(
                  root + (selected ? "/" + selected : ""),
                  selected ? "PATCH" : "POST",
                  payload,
                ),
              async (result) => {
                setForm(null);
                setRows((old) => [
                  ...old.filter((row) => row.id !== result.id),
                  result,
                ]);
                await reloadDetails(result.id);
              },
            );
          }}
        >
          <h3>{selected ? "Edit Workflow" : "New Workflow"}</h3>
          <fieldset disabled={busy || !allowed}>
            <div className="form-grid">
              <label>
                Workflow name
                <input
                  required
                  maxLength={200}
                  value={form.name}
                  onChange={(e) => editField("name", e.target.value)}
                />
              </label>
              <label>
                Environment
                <select
                  aria-label="Workflow environment"
                  value={form.environment}
                  disabled={Boolean(detail?.jobs.length)}
                  onChange={(e) => editField("environment", e.target.value)}
                >
                  {["PROD", "QA", "TEST", "DEV", "SANDBOX"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label>
                Timezone
                <input
                  required
                  value={form.timezone}
                  onChange={(e) => editField("timezone", e.target.value)}
                />
              </label>
              <label>
                Expected start window
                <input
                  type="time"
                  value={form.expected_window_start}
                  onChange={(e) =>
                    editField("expected_window_start", e.target.value)
                  }
                />
              </label>
              <label>
                Expected end window
                <input
                  type="time"
                  value={form.expected_window_end}
                  onChange={(e) =>
                    editField("expected_window_end", e.target.value)
                  }
                />
              </label>
              <label>
                Workflow expected duration seconds
                <input
                  type="number"
                  min="1"
                  max="604800"
                  value={form.expected_duration_seconds}
                  onChange={(e) =>
                    editField("expected_duration_seconds", e.target.value)
                  }
                />
              </label>
              <label>
                Workflow SLA seconds
                <input
                  type="number"
                  min="1"
                  max="604800"
                  value={form.sla_seconds}
                  onChange={(e) => editField("sla_seconds", e.target.value)}
                />
              </label>
            </div>
            <fieldset>
              <legend>Applicable weekdays (Monday = 0)</legend>
              {[
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
              ].map((day, index) => (
                <label key={day}>
                  <input
                    type="checkbox"
                    checked={form.weekdays.includes(index)}
                    onChange={() =>
                      editField(
                        "weekdays",
                        form.weekdays.includes(index)
                          ? form.weekdays.filter((d) => d !== index)
                          : [...form.weekdays, index],
                      )
                    }
                  />
                  {day}{" "}
                </label>
              ))}
            </fieldset>
            <p>
              Frequency / recurrence: BLOCKED — backend contract is not defined.
              Weekdays and windows are monitoring expectations, not scheduler
              instructions.
            </p>
            <button type="submit">Save Workflow</button>
          </fieldset>
          <button type="button" disabled={busy} onClick={() => setForm(null)}>
            Cancel Workflow edit
          </button>
        </form>
      )}
      {detail && (
        <section aria-label="Workflow details">
          <h3>{detail.workflow.name}</h3>
          <p>
            Customer {detail.workflow.organization_id} ·{" "}
            {detail.workflow.environment}
          </p>
          {allowed && !form && (
            <button
              disabled={busy || loading}
              onClick={() => setForm(workflowForm(detail.workflow))}
            >
              Edit Workflow
            </button>
          )}
          <h4>Readiness</h4>
          <dl>
            <dt>Configuration (supported child runtime fields)</dt>
            <dd>{detail.readiness?.configuration_status || "UNVERIFIED"}</dd>
            <dt>Activation</dt>
            <dd>{detail.readiness?.activation_status || "UNVERIFIED"}</dd>
            <dt>Provider connectivity</dt>
            <dd>{detail.readiness?.provider_status || "UNVERIFIED"}</dd>
          </dl>
          <ul>
            {detail.readiness?.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
          <p>
            Saved enabled flags are configuration settings. They do not prove
            active monitoring or healthy workloads.
          </p>
          <h4>Child Jobs</h4>
          {allowed && !job && (
            <button
              disabled={busy || loading}
              onClick={() => setJob(blankJob())}
            >
              Add Job
            </button>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Host identity</th>
                  <th>Expected seconds</th>
                  <th>Telemetry</th>
                  <th>Native execution evidence</th>
                  <th>Configuration</th>
                </tr>
              </thead>
              <tbody>
                {detail.jobs.map((row) => (
                  <tr key={row.id}>
                    <td>{row.name}</td>
                    <td>{row.hostname || "Unbound host"}</td>
                    <td>{row.expected_duration_seconds}</td>
                    <td>{row.telemetry_status || "UNVERIFIED"}</td>
                    <td>
                      {row.latest_execution
                        ? `${row.latest_execution.provider_execution_id || "Identity unverified"} · ${row.latest_execution.status} · observed ${row.latest_execution.detected_at || "time unavailable"}`
                        : "No persisted execution evidence"}
                    </td>
                    <td>
                      {allowed && (
                        <button
                          disabled={busy || loading}
                          onClick={() =>
                            setJob({
                              id: row.id,
                              name: row.name,
                              expected_duration_seconds:
                                row.expected_duration_seconds,
                            })
                          }
                        >
                          Edit Job {row.name}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {job && (
            <form
              aria-label="Job editor"
              onSubmit={(event) => {
                event.preventDefault();
                if (!job.name.trim() || (!job.id && !job.hostname.trim())) {
                  setError("Job name and host identity are required");
                  return;
                }
                const payload = {
                  name: job.name.trim(),
                  expected_duration_seconds: Number(
                    job.expected_duration_seconds,
                  ),
                  ...(!job.id ? { hostname: job.hostname.trim() } : {}),
                };
                save(
                  () =>
                    request(
                      root +
                        "/" +
                        selected +
                        "/jobs" +
                        (job.id ? "/" + job.id : ""),
                      job.id ? "PATCH" : "POST",
                      payload,
                    ),
                  async () => {
                    setJob(null);
                    await reloadDetails(selected);
                  },
                );
              }}
            >
              <h4>{job.id ? "Edit Job" : "New child Job"}</h4>
              <fieldset disabled={busy || !allowed}>
                <p>Parent Workflow: {detail.workflow.name} (immutable)</p>
                <label>
                  Job name
                  <input
                    required
                    maxLength={200}
                    value={job.name}
                    onChange={(e) => setJob({ ...job, name: e.target.value })}
                  />
                </label>
                {!job.id && (
                  <label>
                    Host identity
                    <input
                      required
                      maxLength={200}
                      value={job.hostname}
                      onChange={(e) =>
                        setJob({ ...job, hostname: e.target.value })
                      }
                    />
                  </label>
                )}
                <label>
                  Expected runtime seconds
                  <input
                    required
                    type="number"
                    min="1"
                    max="604800"
                    value={job.expected_duration_seconds}
                    onChange={(e) =>
                      setJob({
                        ...job,
                        expected_duration_seconds: e.target.value,
                      })
                    }
                  />
                </label>
                <p>
                  Native source association and optional separate long-running
                  threshold: BLOCKED — no approved Workflow Job write contract.
                  Use existing pipeline source ownership; names are never native
                  execution identity.
                </p>
                <button type="submit">Save Job</button>
              </fieldset>
              <button
                type="button"
                disabled={busy}
                onClick={() => setJob(null)}
              >
                Cancel Job edit
              </button>
            </form>
          )}
          <h4>Dependencies: predecessor → successor</h4>
          <ul>
            {edges.map((edge) => (
              <li key={edge.id}>
                {detail.jobs.find((j) => j.id === edge.predecessor_job_id)
                  ?.name || "Unavailable Job"}{" "}
                →{" "}
                {detail.jobs.find((j) => j.id === edge.successor_job_id)
                  ?.name || "Unavailable Job"}
              </li>
            ))}
          </ul>
          {!edges.length && <p>No dependencies configured.</p>}
          {allowed && (
            <form
              aria-label="Dependency editor"
              onSubmit={(event) => {
                event.preventDefault();
                const invalid = dependencyError(edges, predecessor, successor);
                if (invalid) {
                  setError(invalid);
                  return;
                }
                save(
                  () =>
                    request(root + "/" + selected + "/dependencies", "POST", {
                      predecessor_job_id: predecessor,
                      successor_job_id: successor,
                    }),
                  () => reloadDetails(selected),
                );
              }}
            >
              <fieldset disabled={busy || loading}>
                <label>
                  Predecessor Job
                  <select
                    aria-label="Predecessor Job"
                    value={predecessor}
                    onChange={(e) => setPredecessor(e.target.value)}
                  >
                    <option value="">Select Job</option>
                    {detail.jobs.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Successor Job
                  <select
                    aria-label="Successor Job"
                    value={successor}
                    onChange={(e) => setSuccessor(e.target.value)}
                  >
                    <option value="">Select Job</option>
                    {detail.jobs.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="submit">Save dependency</button>
              </fieldset>
            </form>
          )}
        </section>
      )}
    </section>
  );
}
