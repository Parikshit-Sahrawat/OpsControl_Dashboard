import { useEffect, useState, useRef } from "react";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
const base = "/api/v1/native-incidents";
const statuses = [
  "OPEN",
  "ACKNOWLEDGED",
  "INVESTIGATING",
  "RECOVERY_IN_PROGRESS",
  "MONITORING",
  "RESOLVED",
  "CLOSED",
];
export default function NativeIncidents({
  organizationIds,
  environment,
  user,
}) {
  const [data, setData] = useState(null),
    [selected, setSelected] = useState(null),
    [status, setStatus] = useState(""),
    [offset, setOffset] = useState(0),
    [error, setError] = useState(""),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false),
    [revision, setRevision] = useState(0),
    [target, setTarget] = useState("ACKNOWLEDGED"),
    [assignee, setAssignee] = useState("");
  const detailGeneration = useRef(0);
  useEffect(() => {
    let live = true;
    setData(null);
    const q = new URLSearchParams({ limit: 50, offset });
    organizationIds.forEach((id) => q.append("organization_id", id));
    if (status) q.set("status", status);
    if (environment) q.set("environment", environment);
    control(base + "?" + q)
      .then((v) => live && setData(v))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [organizationIds.join(","), environment, status, offset, revision]);
  useEffect(() => {
    detailGeneration.current += 1;
    setSelected(null);
    setError("");
  }, [organizationIds.join(","), environment, status, offset]);
  const detail = async (id) => {
    try {
      const generation = ++detailGeneration.current;
      const result = await control(base + "/" + id);
      if (generation !== detailGeneration.current) return;
      setSelected(result);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  };
  const mutate = async (path, payload) => {
    setBusy(true);
    setError("");
    try {
      await control(base + "/" + selected.id + path, "POST", payload);
      await detail(selected.id);
      setNote("");
      setRevision((v) => v + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const can =
    selected &&
    hasPermission(user, "incidents.manage", selected.organization_id);
  return (
    <div className="native-incidents">
      <div className="page-heading">
        <h1>Incidents</h1>
        <button onClick={() => setRevision((v) => v + 1)}>Refresh</button>
      </div>
      <label>
        Status{" "}
        <select
          aria-label="Incident status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!data && !error && <p role="status">Loading incidents…</p>}
      {data && (
        <section className="card table-wrap">
          <table>
            <thead>
              <tr>
                <th>Incident</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Opened</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((i) => (
                <tr key={i.id}>
                  <td>
                    <button onClick={() => detail(i.id)}>{i.title}</button>
                    <small>{i.id}</small>
                  </td>
                  <td>{i.severity}</td>
                  <td>{i.status}</td>
                  <td>{i.opened_at}</td>
                  <td>{i.condition_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.items.length && <p>No incidents in this authorized scope.</p>}
          <button
            disabled={!offset}
            onClick={() => setOffset((v) => Math.max(0, v - 50))}
          >
            Previous
          </button>
          <span>{data.total} incidents</span>
          <button
            disabled={offset + 50 >= data.total}
            onClick={() => setOffset((v) => v + 50)}
          >
            Next
          </button>
        </section>
      )}
      {selected && (
        <section className="card">
          <div className="page-heading">
            <h2>{selected.title}</h2>
            <button onClick={() => setSelected(null)}>Close details</button>
          </div>
          <p>
            {selected.status} · {selected.severity}
          </p>
          {selected.status === "OPEN" &&
            hasPermission(
              user,
              "incidents.acknowledge",
              selected.organization_id,
            ) && (
              <button
                disabled={busy}
                onClick={() =>
                  mutate("/transition", {
                    status: "ACKNOWLEDGED",
                    revision: selected.details.revision,
                  })
                }
              >
                Acknowledge incident
              </button>
            )}
          <h3>Recovery validation</h3>
          <p>
            {selected.recovery?.ready
              ? "Evidence satisfies recovery checks"
              : "Recovery requirements are not yet satisfied"}
          </p>
          <ul>
            {selected.recovery?.reasons?.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
          <h3>Supporting alerts</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Alert</th>
                  <th>State</th>
                  <th>Last evaluated</th>
                </tr>
              </thead>
              <tbody>
                {selected.alerts?.map((a) => (
                  <tr key={a.id}>
                    <td>{a.message}</td>
                    <td>{a.status}</td>
                    <td>{a.last_evaluated_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {can && (
            <div className="incident-actions">
              <label>
                Assigned employee UUID
                <input
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                  placeholder="Existing authorized employee UUID"
                />
              </label>
              <button
                disabled={busy}
                onClick={() =>
                  mutate("/assignment", {
                    assigned_user_id: assignee || null,
                    revision: selected.details.revision,
                  })
                }
              >
                Save assignment
              </button>
              <label>
                Investigation note
                <textarea
                  disabled={busy}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
              <button
                disabled={busy || !note.trim()}
                onClick={() => mutate("/notes", { text: note })}
              >
                Add note
              </button>
              <label>
                Next state
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                >
                  {statuses.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <button
                disabled={busy}
                onClick={() => {
                  if (
                    window.confirm("Change incident state to " + target + "?")
                  )
                    mutate("/transition", {
                      status: target,
                      revision: selected.details.revision,
                      note: note || undefined,
                    });
                }}
              >
                Apply transition
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  mutate("/recovery-validation", {
                    revision: selected.details.revision,
                  })
                }
              >
                Validate recovery evidence
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  mutate("/escalate", {
                    revision: selected.details.revision,
                    note: note || "Operator escalation",
                  })
                }
              >
                Escalate
              </button>
            </div>
          )}
          <h3>Audit timeline</h3>
          <ol>
            {selected.activities?.map((a, i) => (
              <li key={i}>
                {a.occurred_at} · {a.event_type} · {a.text}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
