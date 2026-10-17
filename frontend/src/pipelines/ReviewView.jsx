import { useState } from "react";
import { hasPermission } from "../permissions";
import usePipelineFeed from "./usePipelineFeed";
import { CATEGORIES, resourcePath, reviewActions } from "./contracts";
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
export default function ReviewView({ resource, user }) {
  const [offset, setOffset] = useState(0),
    [category, setCategory] = useState(""),
    [status, setStatus] = useState("OPEN"),
    [selected, setSelected] = useState(null),
    [epoch, setEpoch] = useState(0);
  const q = new URLSearchParams({
      limit: 20,
      offset,
      ...(category ? { category } : {}),
      ...(status ? { status } : {}),
    }),
    feed = usePipelineFeed(
      resourcePath(resource.id) + "/evidence-reviews?" + q,
    );
  return (
    <>
      <div className="pipeline-filters">
        <label>
          Review category
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All six categories</option>
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Review status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All statuses</option>
            {["OPEN", "ACCEPTED", "REJECTED"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      <State feed={feed} empty={!feed.data?.items.length} />
      <Table
        label="Evidence review queue"
        headers={[
          "Category / pipeline",
          "Execution",
          "Claim",
          "Status",
          "Occurred / discovered (UTC)",
          "Revision",
        ]}
      >
        {feed.data?.items.map((r) => (
          <tr key={r.id}>
            <td>
              <button onClick={() => setSelected(r.id)}>{r.category}</button>
              <small>{resource.name}</small>
            </td>
            <td>
              <Identifier value={r.history_id} />
            </td>
            <td>{r.claim}</td>
            <td>
              <Status value={r.status} />
            </td>
            <td>
              <Stamp value={r.context?.occurred_at} />
              <small>
                <Stamp value={r.context?.received_at || r.created_at} />
              </small>
            </td>
            <td>{r.revision}</td>
          </tr>
        ))}
      </Table>
      <Pager total={feed.data?.total} offset={offset} onChange={setOffset} />
      {selected && (
        <ReviewDrawer
          key={selected + epoch}
          resource={resource}
          id={selected}
          user={user}
          onClose={() => setSelected(null)}
          onSaved={() => {
            feed.refresh();
            setEpoch((e) => e + 1);
          }}
        />
      )}
    </>
  );
}
function ReviewDrawer({ resource, id, user, onClose, onSaved }) {
  const [offset, setOffset] = useState(0),
    [action, setAction] = useState("DEFER"),
    feed = usePipelineFeed(
      resourcePath(resource.id) +
        "/evidence-reviews/" +
        id +
        "?limit=20&offset=" +
        offset,
    ),
    r = feed.data?.review,
    allowed =
      r &&
      hasPermission(user, "etl.resolve_identity", resource.organization_id),
    actions = reviewActions(r);
  return (
    <Drawer title="Evidence review details" onClose={onClose}>
      <State feed={feed} />
      {r && (
        <>
          <Facts
            items={{
              Category: r.category,
              Claim: r.claim,
              Status: <Status value={r.status} />,
              Execution: <Identifier value={r.history_id} />,
              Revision: r.revision,
              "Candidate evidence": <Identifier value={r.event_id} />,
              "Raw evidence": <Identifier value={r.source_evidence_id} />,
            }}
          />
          <h3>Previous defensible projection</h3>
          <Evidence value={r.context?.projection_at_conflict} />
          <h3>Conflicting native claim and authority</h3>
          <Evidence
            value={{
              Identity: r.context?.identity,
              Verification: r.context?.verification,
              Issue: r.context?.error,
              Occurred: r.context?.occurred_at,
              Observed: r.context?.observed_at,
              Discovered: r.context?.received_at,
              "Prior evidence revisions": r.context?.prior_revision_ids,
            }}
          />
          {allowed && actions.length ? (
            <MutationForm
              key={r.revision + action}
              label="Submit evidence decision"
              path={
                resourcePath(resource.id) +
                "/evidence-reviews/" +
                r.id +
                "/decision"
              }
              body={(reason, key) => ({
                action,
                reason,
                expected_revision: r.revision,
                idempotency_key: key,
              })}
              onSaved={onSaved}
              disabled={feed.stale || feed.loading}
            >
              <label>
                Decision
                <select
                  value={action}
                  onChange={(e) => setAction(e.target.value)}
                >
                  {actions.map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </label>
              <p>
                Candidate event {r.event_id} is the decision's evidence
                reference. The server verifies native authority; no free-form
                execution outcome is accepted.
              </p>
            </MutationForm>
          ) : (
            <p>
              {allowed
                ? "This review is already decided."
                : "Adjudication requires etl.resolve_identity for this customer."}
            </p>
          )}
          <h3>Reviewer decision history</h3>
          <Table
            label="Review decisions"
            headers={[
              "Revision / action",
              "Reviewer",
              "Reason",
              "Recorded (UTC)",
            ]}
          >
            {feed.data.decisions.map((d) => (
              <tr key={d.id}>
                <td>
                  {d.revision} · {d.action}
                </td>
                <td>
                  <Identifier value={d.actor_id} />
                </td>
                <td>{d.reason}</td>
                <td>
                  <Stamp value={d.created_at} />
                </td>
              </tr>
            ))}
          </Table>
          <Pager
            total={feed.data.total}
            offset={offset}
            onChange={setOffset}
            label="Decisions"
          />
        </>
      )}
    </Drawer>
  );
}
