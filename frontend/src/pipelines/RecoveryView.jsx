import { useState } from "react";
import { hasPermission } from "../permissions";
import usePipelineFeed from "./usePipelineFeed";
import {
  executionPath,
  resourcePath,
  outcome,
  params,
  linkActions,
} from "./contracts";
import {
  State,
  Status,
  Stamp,
  Identifier,
  Facts,
  Pager,
  Table,
  MutationForm,
  Evidence,
} from "./ui";
export default function RecoveryView({ resource, user, initialExecution }) {
  const [offset, setOffset] = useState(0),
    [original, setOriginal] = useState(initialExecution || null),
    [epoch, setEpoch] = useState(0),
    feed = usePipelineFeed(
      resourcePath(resource.id) + "/executions?limit=20&offset=" + offset,
    );
  return (
    <>
      <p>
        Scheduler retries stay within one logical execution. Manual recovery is
        a separate execution and reviewed association; it does not prove
        restored operation.
      </p>
      <State feed={feed} />
      <Table
        label="Recovery execution selection"
        headers={[
          "Execution",
          "Outcome",
          "Type",
          "Identity / review",
          "Recovery tracking",
        ]}
      >
        {feed.data?.items.map((h) => (
          <tr key={h.id}>
            <td>
              <Identifier value={h.id} />
              <small>
                <Stamp value={h.ended_at} />
              </small>
            </td>
            <td>
              <Status value={outcome(h)} />
            </td>
            <td>{h.execution_type}</td>
            <td>
              {h.pentaho_identity_state || "Unknown"}
              <small>{h.pentaho_review_state || "Not reported"}</small>
            </td>
            <td>
              <button
                disabled={!h.pentaho_resource_id || outcome(h) !== "FAILED"}
                onClick={() => {
                  setOriginal(h);
                  setEpoch((e) => e + 1);
                }}
              >
                Track recovery
              </button>
              {outcome(h) === "WAITING_FOR_RETRY" && (
                <small>Retry pending, not a terminal failure</small>
              )}
              {outcome(h) === "SUCCESS_AFTER_RETRY" && (
                <small>Verified scheduler retry success</small>
              )}
            </td>
          </tr>
        ))}
      </Table>
      <Pager total={feed.data?.total} offset={offset} onChange={setOffset} />
      {original && (
        <RecoveryDetail
          key={original.id + epoch}
          resource={resource}
          original={original}
          user={user}
          onSaved={() => {
            setEpoch((e) => e + 1);
            feed.refresh();
          }}
        />
      )}
    </>
  );
}
function RecoveryDetail({ resource, original, user, onSaved }) {
  const [offset, setOffset] = useState(0),
    feed = usePipelineFeed(
      executionPath(resource.id, original.id) +
        "/recovery-links?limit=20&offset=" +
        offset,
    ),
    allowed = hasPermission(
      user,
      "etl.investigate",
      resource.organization_id,
      resource,
    );
  return (
    <section className="pipeline-section" aria-label="Recovery relationships">
      <h2>Original failed execution</h2>
      <Facts
        items={{
          Execution: <Identifier value={original.id} />,
          Outcome: <Status value={outcome(original)} />,
          Pipeline: resource.name,
        }}
      />
      <p>
        The original failure is preserved, including after a separate recovery
        succeeds.
      </p>
      <State feed={feed} empty={!feed.data?.items.length} />
      {feed.data?.items.map((link) => (
        <section className="pipeline-section" key={link.id}>
          <Facts
            items={{
              Association: <Identifier value={link.id} />,
              Status: <Status value={link.status} />,
              Original: <Identifier value={link.failed_history_id} />,
              "Separate recovery": (
                <Identifier value={link.recovery_history_id} />
              ),
              Proposer: <Identifier value={link.proposed_by} />,
              Revision: link.revision,
            }}
          />
          {link.status === "PROPOSED" && link.proposed_by === user.id && (
            <p>
              Independent confirmation required. You cannot confirm your own
              proposal.
            </p>
          )}
          {allowed &&
            linkActions(link, user.id).map((action) => (
              <MutationForm
                key={action}
                label={
                  action === "CONFIRM"
                    ? "Confirm recovery association"
                    : "Reverse recovery association"
                }
                path={
                  executionPath(resource.id, link.failed_history_id) +
                  "/recovery-links/" +
                  link.id +
                  "/decision"
                }
                body={(reason, key) => ({
                  action,
                  reason,
                  expected_revision: link.revision,
                  idempotency_key: key,
                })}
                onSaved={onSaved}
                disabled={feed.stale || feed.loading}
              />
            ))}
          <details>
            <summary>Association decision audit</summary>
            {link.decisions.map((d) => (
              <Facts
                key={d.id}
                items={{
                  Action: d.action,
                  Reviewer: <Identifier value={d.actor_id} />,
                  Reason: d.reason,
                  Evidence: <Evidence value={d.evidence} />,
                  Recorded: <Stamp value={d.created_at} />,
                }}
              />
            ))}
          </details>
        </section>
      ))}
      <Pager
        total={feed.data?.total}
        offset={offset}
        onChange={setOffset}
        label="Recovery links"
      />
      {allowed ? (
        <Proposal resource={resource} original={original} onSaved={onSaved} />
      ) : (
        <p>Recovery-link actions require etl.investigate for this customer.</p>
      )}
    </section>
  );
}
function Proposal({ resource, original, onSaved }) {
  const [candidateResource, setCandidateResource] = useState(resource.id),
    [resourceOffset, setResourceOffset] = useState(0),
    [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0),
    [candidate, setCandidate] = useState(""),
    [evidence, setEvidence] = useState([]),
    [attemptOffset, setAttemptOffset] = useState(0),
    [candidateAttemptOffset, setCandidateAttemptOffset] = useState(0);
  const resources = usePipelineFeed(
      "/api/v1/unified/resources?" +
        params([resource.organization_id], resource.environment, {
          domain: "ETL",
          search,
          limit: 20,
          offset: resourceOffset,
        }),
    ),
    candidates = usePipelineFeed(
      resourcePath(candidateResource) + "/executions?limit=20&offset=" + offset,
    ),
    failed = usePipelineFeed(
      executionPath(resource.id, original.id) +
        "/attempts?limit=20&offset=" +
        attemptOffset,
    ),
    recovered = usePipelineFeed(
      candidate
        ? executionPath(candidateResource, candidate) +
            "/attempts?limit=20&offset=" +
            candidateAttemptOffset
        : null,
    );
  const originalEvidence = (failed.data?.items || [])
      .flatMap((a) => a.revisions || [])
      .filter((r) => r.disposition === "ACCEPTED"),
    candidateEvidence = (recovered.data?.items || [])
      .flatMap((a) => a.revisions || [])
      .filter((r) => r.disposition === "ACCEPTED");
  const canPropose =
    candidate &&
    originalEvidence.some((r) => evidence.includes(r.event_id)) &&
    candidateEvidence.some((r) => evidence.includes(r.event_id)) &&
    evidence.length <= 25 &&
    ![failed, recovered, resources, candidates].some(
      (f) => f.stale || f.loading || f.error,
    );
  return (
    <section className="pipeline-section">
      <h3>Propose a separate recovery</h3>
      <p>
        Choose accepted evidence from both executions. Only this customer's
        resources are offered. Native identity and authority are verified by the
        server.
      </p>
      <div className="pipeline-filters">
        <label>
          Find recovery pipeline
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setResourceOffset(0);
            }}
          />
        </label>
        <label>
          Recovery pipeline
          <select
            value={candidateResource}
            onChange={(e) => {
              setCandidateResource(e.target.value);
              setCandidate("");
              setEvidence([]);
              setOffset(0);
            }}
          >
            <option value={resource.id}>{resource.name}</option>
            {resources.data?.items
              .filter((r) => r.id !== resource.id)
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
          </select>
        </label>
      </div>
      <State feed={resources} />
      <Pager
        total={resources.data?.total}
        offset={resourceOffset}
        onChange={setResourceOffset}
        label="Recovery pipelines"
      />
      <State feed={candidates} />
      <label>
        Separate successful execution
        <select
          value={candidate}
          onChange={(e) => {
            setCandidate(e.target.value);
            setEvidence([]);
            setCandidateAttemptOffset(0);
          }}
        >
          <option value="">Select verified native recovery candidate</option>
          {candidates.data?.items
            .filter(
              (h) =>
                h.id !== original.id &&
                h.pentaho_identity_state === "CONFIRMED" &&
                ["SUCCESS", "SUCCESS_AFTER_RETRY"].includes(outcome(h)) &&
                !["CONFLICTED_EVIDENCE", "REVIEW_REQUIRED"].includes(
                  h.pentaho_review_state,
                ),
            )
            .map((h) => (
              <option key={h.id} value={h.id}>
                {h.id} · {outcome(h)}
              </option>
            ))}
        </select>
      </label>
      <Pager
        total={candidates.data?.total}
        offset={offset}
        onChange={setOffset}
        label="Recovery executions"
      />
      <State feed={failed} />
      <State feed={recovered} />
      {[
        ["Original failure evidence", originalEvidence],
        ["Separate recovery evidence", candidateEvidence],
      ].map(([name, rows]) => (
        <fieldset key={name}>
          <legend>{name}</legend>
          {rows.map((r) => (
            <label className="pipeline-confirm" key={r.id}>
              <input
                type="checkbox"
                checked={evidence.includes(r.event_id)}
                onChange={(e) =>
                  setEvidence((v) =>
                    e.target.checked
                      ? [...new Set([...v, r.event_id])]
                      : v.filter((id) => id !== r.event_id),
                  )
                }
              />
              <Identifier value={r.event_id} /> ·{" "}
              {r.payload?.identity?.native_outcome || r.disposition}
            </label>
          ))}
          {!rows.length && <p>No accepted evidence on this attempt page.</p>}
        </fieldset>
      ))}
      <Pager
        total={failed.data?.total}
        offset={attemptOffset}
        onChange={setAttemptOffset}
        label="Failure attempt evidence"
      />
      <Pager
        total={recovered.data?.total}
        offset={candidateAttemptOffset}
        onChange={setCandidateAttemptOffset}
        label="Recovery attempt evidence"
      />
      <MutationForm
        label="Propose recovery association"
        path={executionPath(resource.id, original.id) + "/recovery-links"}
        body={(reason, key) => ({
          recovery_history_id: candidate,
          evidence_ids: evidence,
          reason,
          idempotency_key: key,
        })}
        onSaved={onSaved}
        disabled={!canPropose}
      />
    </section>
  );
}
