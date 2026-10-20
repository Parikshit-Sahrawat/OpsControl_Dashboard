import { useState } from "react";
import { hasPermission } from "../permissions";
import usePipelineFeed from "./usePipelineFeed";
import { params, INCIDENT_TRANSITIONS } from "./contracts";
import {
  State,
  Status,
  Stamp,
  Identifier,
  Facts,
  Pager,
  Table,
  Drawer,
  Evidence,
  MutationForm,
} from "./ui";
export default function IncidentView({ organizationIds, environment, user }) {
  const [status, setStatus] = useState(""),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState(null),
    [epoch, setEpoch] = useState(0),
    ids = organizationIds.filter((id) =>
      hasPermission(user, "incidents.view", id),
    ),
    feed = usePipelineFeed(
      ids.length
        ? "/api/v1/native-incidents?" +
            params(ids, environment, { status, limit: 20, offset })
        : null,
    );
  if (!ids.length)
    return (
      <p role="status">
        Incident correlation requires incidents.view in the selected customer
        scope.
      </p>
    );
  return (
    <>
      <div className="pipeline-filters">
        <label>
          Incident lifecycle
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All seven states</option>
            {Object.keys(INCIDENT_TRANSITIONS).map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <span>
          Customer-scoped native incidents. Details show exact execution
          associations.
        </span>
      </div>
      <State feed={feed} empty={!feed.data?.items.length} />
      <Table
        label="Native incident correlation"
        headers={[
          "Incident",
          "Customer / environment scope",
          "Lifecycle",
          "Severity",
          "Assigned employee",
          "Opened (UTC)",
        ]}
      >
        {feed.data?.items.map((i) => (
          <tr key={i.id}>
            <td>
              <button onClick={() => setSelected(i.id)}>{i.title}</button>
              <small>
                <Identifier value={i.id} />
              </small>
            </td>
            <td>
              <Identifier value={i.organization_id} />
              <small>
                {Array.isArray(environment)
                  ? environment.length ? environment.join(", ") : "All selected environments · see resource evidence"
                  : environment || "All selected environments · see resource evidence"}
              </small>
            </td>
            <td>
              <Status value={i.status} />
            </td>
            <td>
              <Status value={i.severity} />
            </td>
            <td>
              <Identifier value={i.details?.assigned_user_id} />
            </td>
            <td>
              <Stamp value={i.opened_at} />
            </td>
          </tr>
        ))}
      </Table>
      <Pager total={feed.data?.total} offset={offset} onChange={setOffset} />
      {selected && (
        <IncidentDrawer
          key={selected + epoch}
          id={selected}
          user={user}
          onClose={() => setSelected(null)}
          onSaved={() => {
            setEpoch((v) => v + 1);
            feed.refresh();
          }}
        />
      )}
    </>
  );
}
function IncidentDrawer({ id, user, onClose, onSaved }) {
  const [tab, setTab] = useState("Failures"),
    [offset, setOffset] = useState(0),
    [assignee, setAssignee] = useState(""),
    [observation, setObservation] = useState(60),
    [note, setNote] = useState(""),
    base = "/api/v1/native-incidents/" + id,
    feed = usePipelineFeed(base),
    i = feed.data;
  const failures = usePipelineFeed(
      tab === "Failures"
        ? base + "/execution-failures?limit=20&offset=" + offset
        : null,
    ),
    assessments = usePipelineFeed(
      tab === "Recovery"
        ? base + "/recovery-assessments?limit=20&offset=" + offset
        : null,
    ),
    activities = usePipelineFeed(
      tab === "Audit" ? base + "/activities?limit=20&offset=" + offset : null,
    ),
    can = i && hasPermission(user, "incidents.manage", i.organization_id),
    revision = i?.details?.revision,
    blocked = feed.stale || feed.loading;
  return (
    <Drawer title="Incident correlation details" onClose={onClose}>
      <State feed={feed} />
      {i && (
        <>
          <Facts
            items={{
              Incident: <Identifier value={i.id} />,
              Lifecycle: <Status value={i.status} />,
              Severity: i.severity,
              Customer: <Identifier value={i.organization_id} />,
              Owner: <Identifier value={i.details?.assigned_user_id} />,
              Revision: revision,
            }}
          />
          <nav className="pipeline-tabs" aria-label="Incident detail sections">
            {["Failures", "Recovery", "Audit", "Investigation"].map((t) => (
              <button
                key={t}
                aria-current={tab === t ? "page" : undefined}
                onClick={() => {
                  setTab(t);
                  setOffset(0);
                }}
              >
                {t}
              </button>
            ))}
          </nav>
          {tab === "Failures" && (
            <>
              <State feed={failures} empty={!failures.data?.items.length} />
              <Table
                label="Correlated failed executions"
                headers={[
                  "Failed execution / pipeline",
                  "Occurred / discovered (UTC)",
                  "Classification",
                  "Common-root evidence",
                ]}
              >
                {failures.data?.items.map((f) => (
                  <tr key={f.id}>
                    <td>
                      <Identifier value={f.history_id} />
                      <small>
                        Resource <Identifier value={f.resource_id} />
                      </small>
                    </td>
                    <td>
                      <Stamp value={f.occurred_at} />
                      <small>
                        <Stamp value={f.discovered_at} />
                      </small>
                    </td>
                    <td>
                      {f.reassessment?.action
                        ? "Historical reassessment"
                        : "Operational failure"}
                      <small>
                        {f.reassessment?.incident_status
                          ? "Retained state: " + f.reassessment.incident_status
                          : ""}
                      </small>
                    </td>
                    <td>
                      {f.root_key ? (
                        <details>
                          <summary>Verified native cause reference</summary>
                          <Evidence value={f.evidence?.failure_cause} />
                        </details>
                      ) : (
                        "Distinct execution · no common root asserted"
                      )}
                      <details>
                        <summary>Failure provenance</summary>
                        <Evidence value={f.evidence} />
                      </details>
                    </td>
                  </tr>
                ))}
              </Table>
              <Pager
                total={failures.data?.total}
                offset={offset}
                onChange={setOffset}
                label="Incident failures"
              />
            </>
          )}
          {tab === "Recovery" && (
            <>
              <h3>Recovery assessment, independent of lifecycle</h3>
              <Status value={i.recovery?.result || "UNKNOWN"} />
              <p>
                {i.recovery?.ready
                  ? "Backend checks currently permit an authorized lifecycle decision. The incident is not automatically closed."
                  : "Restoration is not verified. Successful execution or a recovery association alone is insufficient."}
              </p>
              <ul>
                {i.recovery?.reasons?.map((r, n) => (
                  <li key={n}>{r}</li>
                ))}
              </ul>
              <Facts
                items={{
                  "Observation period":
                    (i.recovery?.evidence?.observation_seconds ??
                      i.details.monitoring_seconds) + " seconds",
                  "Healthy since": (
                    <Stamp value={i.recovery?.evidence?.healthy_since} />
                  ),
                  "Checked at": (
                    <Stamp value={i.recovery?.evidence?.checked_at} />
                  ),
                }}
              />
              <h3>Required dependencies and schedule checks</h3>
              <Evidence
                value={{
                  Dependencies: i.recovery?.evidence?.dependencies,
                  Schedules: i.recovery?.evidence?.schedules,
                  "Confirmed execution candidates":
                    i.recovery?.evidence?.candidates,
                }}
              />
              {can && (
                <MutationForm
                  label="Record recovery assessment"
                  path={base + "/recovery-assessments"}
                  body={(_reason, key) => ({
                    revision,
                    idempotency_key: key,
                    observation_seconds: Number(observation),
                  })}
                  reasonRequired={false}
                  disabled={blocked || !i.execution_failures?.length}
                  onSaved={onSaved}
                >
                  <label>
                    Observation period (seconds)
                    <input
                      type="number"
                      min="60"
                      max="86400"
                      required
                      value={observation}
                      onChange={(e) => setObservation(e.target.value)}
                    />
                  </label>
                  <p>
                    This records the server assessment, including pending or
                    failed validation; it does not declare restoration.
                  </p>
                </MutationForm>
              )}
              {can && i.status === "MONITORING" && (
                <MutationForm
                  label="Validate recovery evidence"
                  path={base + "/recovery-validation"}
                  body={{ revision }}
                  reasonRequired={false}
                  disabled={blocked || !i.recovery?.ready}
                  onSaved={onSaved}
                />
              )}
              <State feed={assessments} />
              <Table
                label="Recovery assessment history"
                headers={[
                  "Result",
                  "Reviewer",
                  "Observation",
                  "Assessed (UTC)",
                ]}
              >
                {assessments.data?.items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Status value={a.result} />
                    </td>
                    <td>
                      <Identifier value={a.actor_id} />
                    </td>
                    <td>
                      {a.evidence?.observation_seconds}s
                      <small>
                        <Stamp value={a.evidence?.healthy_since} />
                      </small>
                    </td>
                    <td>
                      <Stamp value={a.assessed_at} />
                    </td>
                  </tr>
                ))}
              </Table>
              <Pager
                total={assessments.data?.total}
                offset={offset}
                onChange={setOffset}
                label="Assessments"
              />
            </>
          )}
          {tab === "Audit" && (
            <>
              <p>
                Retained native lifecycle, correlation and recovery activities.
              </p>
              <State feed={activities} />
              <Table
                label="Incident audit history"
                headers={[
                  "Activity",
                  "Actor",
                  "Transition / detail",
                  "Recorded (UTC)",
                ]}
              >
                {activities.data?.items.map((a) => (
                  <tr key={a.id}>
                    <td>{a.event_type}</td>
                    <td>{a.actor}</td>
                    <td>
                      {a.previous_status
                        ? `${a.previous_status} → ${a.new_status}`
                        : a.new_status}
                      <small>{a.text}</small>
                    </td>
                    <td>
                      <Stamp value={a.occurred_at} />
                    </td>
                  </tr>
                ))}
              </Table>
            </>
          )}
          {tab === "Audit" && (
            <Pager
              total={activities.data?.total}
              offset={offset}
              onChange={setOffset}
              label="Activities"
            />
          )}
          {tab === "Investigation" && (
            <>
              {!can && (
                <p>
                  Investigation changes require incidents.manage. Acknowledge
                  requires its separate permission.
                </p>
              )}
              {(INCIDENT_TRANSITIONS[i.status] || [])
                .filter((t) =>
                  hasPermission(
                    user,
                    t === "ACKNOWLEDGED"
                      ? "incidents.acknowledge"
                      : "incidents.manage",
                    i.organization_id,
                  ),
                )
                .map((target) => (
                  <MutationForm
                    key={target}
                    label={"Transition to " + target}
                    path={base + "/transition"}
                    body={(reason) => ({
                      revision,
                      status: target,
                      note: reason,
                    })}
                    disabled={
                      blocked ||
                      (["RESOLVED", "CLOSED"].includes(target) &&
                        !i.recovery?.ready)
                    }
                    onSaved={onSaved}
                  >
                    {["RESOLVED", "CLOSED"].includes(target) &&
                      !i.recovery?.ready && (
                        <p>Unavailable until backend recovery checks pass.</p>
                      )}
                    {target === "OPEN" && (
                      <p>
                        This explicitly reopens an incident. Historical evidence
                        never reopens it automatically.
                      </p>
                    )}
                  </MutationForm>
                ))}
              {can && (
                <>
                  <MutationForm
                    label="Add investigation note"
                    path={base + "/notes"}
                    body={() => ({ text: note })}
                    reasonRequired={false}
                    disabled={blocked}
                    onSaved={onSaved}
                  >
                    <label>
                      Investigation note
                      <textarea
                        required
                        maxLength={4000}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                      />
                    </label>
                  </MutationForm>
                  <MutationForm
                    label="Assign incident owner"
                    path={base + "/assignment"}
                    body={() => ({
                      revision,
                      assigned_user_id: assignee || null,
                    })}
                    reasonRequired={false}
                    disabled={blocked}
                    onSaved={onSaved}
                  >
                    <label>
                      Authorized employee ID
                      <input
                        value={assignee}
                        onChange={(e) => setAssignee(e.target.value)}
                        placeholder="Leave blank to unassign"
                        pattern="[0-9a-fA-F-]{36}"
                      />
                    </label>
                  </MutationForm>
                  {i.status !== "CLOSED" && (
                    <MutationForm
                      label="Escalate incident"
                      path={base + "/escalate"}
                      body={(reason) => ({ revision, note: reason })}
                      disabled={blocked}
                      onSaved={onSaved}
                    />
                  )}
                </>
              )}
            </>
          )}
        </>
      )}
    </Drawer>
  );
}
