import { useState } from "react";
import { hasPermission } from "../permissions";
import usePipelineFeed from "./usePipelineFeed";
import {
  executionPath,
  resourcePath,
  outcome,
  OUTCOMES,
  duration,
  params,
} from "./contracts";
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
} from "./ui";
export function ExecutionHistory({ resource, user, onRecovery }) {
  const [offset, setOffset] = useState(0),
    [filter, setFilter] = useState(""),
    [selected, setSelected] = useState(null);
  const feed = usePipelineFeed(
      resourcePath(resource.id) + "/executions?limit=20&offset=" + offset,
    ),
    rows = (feed.data?.items || []).filter(
      (h) => !filter || outcome(h) === filter,
    );
  return (
    <>
      <div className="pipeline-filters">
        <label>
          Outcome on this page
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All outcomes</option>
            {OUTCOMES.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <span>Server pagination · outcome filter applies to this page.</span>
      </div>
      <State feed={feed} empty={!rows.length} />
      <Table
        label="Execution history"
        headers={[
          "Logical execution / pipeline",
          "Start / end (UTC)",
          "Duration",
          "Lifecycle / outcome",
          "Type / retry",
          "Attempts",
          "Completeness / review",
          "Incident",
        ]}
      >
        {rows.map((h) => (
          <tr key={h.id}>
            <td>
              <button onClick={() => setSelected(h)}>
                <Identifier value={h.id} />
              </button>
              <small>{resource.name}</small>
            </td>
            <td>
              <Stamp value={h.started_at} />
              <small>
                <Stamp value={h.ended_at} />
              </small>
            </td>
            <td>{duration(h)}</td>
            <td>
              {h.pentaho_lifecycle || "Native lifecycle unreported"}
              <small>
                <Status value={outcome(h)} />
              </small>
            </td>
            <td>
              {h.execution_type || "Unknown"}
              <small>
                {h.pentaho_lifecycle === "WAITING_FOR_RETRY"
                  ? "Retry pending · nonterminal"
                  : outcome(h) === "SUCCESS_AFTER_RETRY"
                    ? "Verified scheduler retry"
                    : "See retry authority in attempts"}
              </small>
            </td>
            <td>
              <AttemptCount resource={resource} history={h} />
            </td>
            <td>
              <Status value={h.pentaho_completeness || "UNKNOWN"} />
              <small>
                <Status value={h.pentaho_review_state || "UNKNOWN"} />
              </small>
            </td>
            <td>{h.incident_number || "See Incidents tab"}</td>
          </tr>
        ))}
      </Table>
      <Pager total={feed.data?.total} offset={offset} onChange={setOffset} />
      {selected && (
        <ExecutionDrawer
          resource={resource}
          history={selected}
          user={user}
          onClose={() => setSelected(null)}
          onRecovery={onRecovery}
        />
      )}
    </>
  );
}
function AttemptCount({ resource, history }) {
  const feed = usePipelineFeed(
    history.pentaho_resource_id
      ? executionPath(resource.id, history.id) + "/attempts?limit=1&offset=0"
      : null,
  );
  return (
    <span
      title={
        feed.error
          ? "Attempt count unavailable"
          : feed.stale
            ? "Stale count"
            : undefined
      }
    >
      {history.pentaho_resource_id
        ? feed.error
          ? "Unavailable"
          : (feed.data?.total ?? "Loading")
        : "Not exposed"}
    </span>
  );
}
export function ExecutionDrawer({
  resource,
  history,
  user,
  onClose,
  onRecovery,
}) {
  const [tab, setTab] = useState("Overview"),
    [offset, setOffset] = useState(0),
    native = Boolean(history.pentaho_resource_id);
  const attempts = usePipelineFeed(
      native
        ? executionPath(resource.id, history.id) +
            "/attempts?limit=20&offset=" +
            offset
        : null,
    ),
    legacy = usePipelineFeed(
      !native ? "/api/v1/etl/executions/" + history.id : null,
    );
  const h = attempts.data?.execution || history,
    revisions = (attempts.data?.items || []).flatMap((a) => a.revisions || []),
    steps = history.steps?.length ? history.steps : legacy.data?.steps || [];
  return (
    <Drawer title="Execution details" onClose={onClose}>
      <div className="pipeline-detail-title">
        <Identifier value={h.id} />
        <Status value={outcome(h)} />
        <p>
          {resource.name} · {resource.environment}
        </p>
      </div>
      <nav className="pipeline-tabs" aria-label="Execution detail sections">
        {[
          "Overview",
          "Attempts",
          "Evidence",
          ...(steps.length ? ["Steps"] : []),
          "Incidents",
          "Audit",
        ].map((t) => (
          <button
            key={t}
            aria-current={tab === t ? "page" : undefined}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>
      <State feed={native ? attempts : legacy} />
      {tab === "Overview" && (
        <>
          <Facts
            items={{
              "Logical execution": <Identifier value={h.id} />,
              Lifecycle: h.pentaho_lifecycle || "Not reported",
              Outcome: <Status value={outcome(h)} />,
              Type: h.execution_type,
              "Attempt count": native
                ? (attempts.data?.total ?? "Loading")
                : "Not exposed",
              Started: <Stamp value={h.started_at} />,
              Ended: <Stamp value={h.ended_at} />,
              Duration: duration(h),
              Completeness: (
                <Status value={h.pentaho_completeness || "UNKNOWN"} />
              ),
              Review: <Status value={h.pentaho_review_state || "UNKNOWN"} />,
            }}
          />
          <p>
            Execution outcome, monitoring health and incident restoration are
            separate. Manual recovery never changes the original failed
            execution.
          </p>
          {!steps.length && (
            <p>
              No verified step observations are available; the Steps tab is not
              enabled.
            </p>
          )}
          {native && outcome(h) === "FAILED" && onRecovery && (
            <button
              onClick={() => {
                onClose();
                onRecovery(h);
              }}
            >
              View recovery relationships
            </button>
          )}
        </>
      )}
      {tab === "Attempts" &&
        (native ? (
          <>
            <p>
              {attempts.data?.total ?? "…"} canonical attempts. Scheduler
              retries belong to this execution; manual reruns have separate
              execution IDs.
            </p>
            <Table
              label="Execution attempts"
              headers={[
                "Attempt",
                "Outcome",
                "Completeness",
                "Retry authority",
                "Native invocation",
                "Start / end (UTC)",
              ]}
            >
              {attempts.data?.items.map((a) => (
                <tr key={a.id}>
                  <td>
                    {a.attempt_order}
                    <small>
                      <Identifier value={a.id} />
                    </small>
                  </td>
                  <td>
                    <Status value={a.outcome} />
                  </td>
                  <td>{a.completeness}</td>
                  <td>
                    {a.retry_authority?.retry_state ||
                      a.native_identity?.scheduler?.retry_state ||
                      "Not reported"}
                  </td>
                  <td>
                    <Identifier
                      value={a.native_identity?.native_execution_id}
                    />
                  </td>
                  <td>
                    <Stamp value={a.started_at} />
                    <small>
                      <Stamp value={a.ended_at} />
                    </small>
                  </td>
                </tr>
              ))}
            </Table>
            <Pager
              total={attempts.data?.total}
              offset={offset}
              onChange={setOffset}
              label="Attempts"
            />
          </>
        ) : (
          <p>
            Canonical attempt detail is not exposed for this platform. Existing
            execution evidence is preserved.
          </p>
        ))}
      {tab === "Evidence" && (
        <>
          <p>
            Native revisions retain authority, scope and acceptance provenance.
            No outcome override is available.
          </p>
          {revisions.map((r) => (
            <details key={r.id}>
              <summary>
                Revision {r.revision} · {r.disposition} · {r.event_id}
              </summary>
              <Evidence
                value={{
                  Event: r.event_id,
                  "Raw evidence": r.source_evidence_id,
                  Recorded: r.created_at,
                  "Native identity": r.payload?.identity,
                  Verification: r.payload?.verification,
                }}
              />
            </details>
          ))}
          {!revisions.length && (
            <Evidence
              value={h.source_evidence || legacy.data?.source_evidence}
            />
          )}{" "}
          {native && (
            <Pager
              total={attempts.data?.total}
              offset={offset}
              onChange={setOffset}
              label="Evidence attempts"
            />
          )}
        </>
      )}
      {tab === "Steps" && (
        <Table
          label="Observed steps"
          headers={["Step", "Status", "Type", "Duration"]}
        >
          {steps.map((s, i) => (
            <tr key={s.id || i}>
              <td>{s.name}</td>
              <td>
                <Status value={s.status} />
              </td>
              <td>{s.step_type || "Not reported"}</td>
              <td>
                {s.duration_seconds == null
                  ? "Unknown"
                  : s.duration_seconds + "s"}
              </td>
            </tr>
          ))}
        </Table>
      )}
      {tab === "Audit" && (
        <>
          <p>
            Append-only execution revisions, including preserved claims and
            dispositions. Each attempt exposes up to 100 revisions and 200
            aliases.
          </p>
          <Table
            label="Execution revision audit"
            headers={["Revision", "Disposition", "Evidence", "Recorded (UTC)"]}
          >
            {revisions.map((r) => (
              <tr key={r.id}>
                <td>{r.revision}</td>
                <td>{r.disposition}</td>
                <td>
                  <Identifier value={r.event_id} />
                </td>
                <td>
                  <Stamp value={r.created_at} />
                </td>
              </tr>
            ))}
          </Table>
          {native ? (
            <Pager
              total={attempts.data?.total}
              offset={offset}
              onChange={setOffset}
              label="Attempt audit"
            />
          ) : (
            <p>Canonical revision audit is not exposed for this platform.</p>
          )}
        </>
      )}
      {tab === "Incidents" && (
        <ExecutionIncidents resource={resource} history={h} user={user} />
      )}
    </Drawer>
  );
}
function ExecutionIncidents({ resource, history, user }) {
  const [offset, setOffset] = useState(0),
    allowed = hasPermission(
      user,
      "incidents.view",
      resource.organization_id,
      resource,
    );
  const feed = usePipelineFeed(
    allowed
      ? "/api/v1/native-incidents?" +
          params([resource.organization_id], resource.environment, {
            limit: 20,
            offset,
          })
      : null,
  );
  return !allowed ? (
    <p>Incident evidence requires incidents.view for this customer.</p>
  ) : (
    <>
      <State feed={feed} />
      <p>
        Customer-scoped incidents, 20 per page. Open failure evidence to check
        the exact execution ID; the list does not assert unrelated incidents as
        correlations.
      </p>
      {feed.data?.items.map((i) => (
        <IncidentMatch key={i.id} incident={i} history={history} />
      ))}
      <Pager
        total={feed.data?.total}
        offset={offset}
        onChange={setOffset}
        label="Scoped incidents"
      />
    </>
  );
}
function IncidentMatch({ incident, history }) {
  const [open, setOpen] = useState(false),
    [offset, setOffset] = useState(0),
    feed = usePipelineFeed(
      open
        ? `/api/v1/native-incidents/${incident.id}/execution-failures?limit=20&offset=${offset}`
        : null,
    );
  return (
    <details onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>
        {incident.title} · {incident.status}
      </summary>
      <State feed={feed} />
      {feed.data?.items.map((f) => (
        <div key={f.id}>
          <strong>
            {f.history_id === history.id ? "This execution" : "Other execution"}
          </strong>{" "}
          <Identifier value={f.history_id} />
          <Evidence value={f.evidence?.failure_cause} />
        </div>
      ))}
      <Pager
        total={feed.data?.total}
        offset={offset}
        onChange={setOffset}
        label="Failure associations"
      />
    </details>
  );
}
