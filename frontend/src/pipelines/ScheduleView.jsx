import { useState } from "react";
import usePipelineFeed from "./usePipelineFeed";
import { resourcePath, scheduleAuthority } from "./contracts";
import {
  State,
  Status,
  Stamp,
  Table,
  Identifier,
  Evidence,
  Pager,
  Drawer,
} from "./ui";
export default function ScheduleView({ resource }) {
  const [filter, setFilter] = useState(""),
    [selected, setSelected] = useState(null),
    [offset, setOffset] = useState(0),
    feed = usePipelineFeed(
      resourcePath(resource.id) +
        "/schedule-occurrences?limit=20&offset=" +
        offset +
        (filter ? "&status=" + filter : ""),
    ),
    rows = feed.data?.items || [];
  return (
    <>
      <div className="pipeline-filters">
        <label>
          Schedule compliance
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All states</option>
            {[
              "PENDING_GRACE",
              "OBSERVED",
              "DELAYED",
              "NO_RUN",
              "UNKNOWN",
              "INCOMPLETE",
            ].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <span>Server pagination across retained schedule occurrences.</span>
      </div>
      <State feed={feed} empty={!rows.length} />
      <Table
        label="Schedule occurrences"
        headers={[
          "Pipeline / authority",
          "Expected (UTC)",
          "Timezone / DST",
          "Grace",
          "Execution",
          "Compliance",
          "Coverage",
          "Evaluated (UTC)",
        ]}
      >
        {rows.map((w) => {
          const a = scheduleAuthority(w),
            c = a.snapshot.calendar || {};
          return (
            <tr key={w.id}>
              <td>
                <button onClick={() => setSelected(w)}>{resource.name}</button>
                <small>{a.label}</small>
              </td>
              <td>
                <Stamp value={w.scheduled_at} />
              </td>
              <td>
                {c.timezone || "Not reported"}
                <small>{c.dst_policy || "DST policy unreported"}</small>
              </td>
              <td>
                {a.snapshot.grace_seconds == null
                  ? "Unreported"
                  : a.snapshot.grace_seconds + "s"}
              </td>
              <td>
                <Identifier value={w.history_id} />
              </td>
              <td>
                <Status value={w.status} />
              </td>
              <td>
                {w.evidence?.coverage?.ready === true
                  ? "Coverage confirmed"
                  : w.evidence?.coverage?.ready === false
                    ? "Coverage incomplete"
                    : "Coverage unknown"}
              </td>
              <td>
                <Stamp value={w.evaluated_at} />
              </td>
            </tr>
          );
        })}
      </Table>
      <Pager
        total={feed.data?.total}
        offset={offset}
        onChange={setOffset}
        label="Occurrences"
      />
      <p>
        NO_RUN appears only when returned by the schedule evaluator. Empty
        execution history or successful HTTP responses cannot establish a missed
        run.
      </p>
      {selected && (
        <Drawer title="Schedule evidence" onClose={() => setSelected(null)}>
          <h3>{scheduleAuthority(selected).label}</h3>
          <Status value={selected.status} />
          {["UNKNOWN", "INCOMPLETE"].includes(selected.status) && (
            <p>
              Native authority or complete source coverage is unavailable.
              Missing telemetry does not prove a missed execution.
            </p>
          )}
          <Evidence
            value={{
              Authority: selected.pentaho_authority,
              Coverage: selected.evidence,
              Deadline: selected.deadline,
              "Observed execution": selected.history_id,
              "Last evaluation": selected.evaluated_at,
            }}
          />
        </Drawer>
      )}
    </>
  );
}
