import { useState } from "react";
import { useOperationalFeed, scopeQuery, evidenceTime } from "../operations";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
export default function Alerts({ organizationIds, user }) {
  const { data, error, refresh } = useOperationalFeed(
    "/alerts?" + scopeQuery(organizationIds),
  );
  const [failure, setFailure] = useState(""),
    [filter, setFilter] = useState("ALL"),
    [search, setSearch] = useState(""),
    [busy, setBusy] = useState(false);
  const acknowledge = async (row) => {
    if (
      !window.confirm(
        "Acknowledge this monitoring alert? Recovery still depends on telemetry.",
      )
    )
      return;
    setBusy(true);
    try {
      await control(
        "/api/v1/operations/alerts/" + row.id + "/acknowledge",
        "POST",
      );
      refresh();
    } catch (e) {
      setFailure(e.message);
    } finally {
      setBusy(false);
    }
  };
  const rows = (data?.alerts || []).filter(
    (row) =>
      (filter === "ALL" || row.status === filter) &&
      row.message.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="operations-page">
      <div className="page-heading">
        <h1>Alerts</h1>
        <button onClick={refresh}>Refresh</button>
      </div>
      <div className="operational-filters">
        <input
          aria-label="Search alerts"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search monitoring alerts"
        />
        <select
          aria-label="Alert status"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          {["ALL", "OPEN", "RESOLVED"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      {(error || failure) && <p role="alert">{error || failure}</p>}
      <section className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Alert</th>
              <th>Severity</th>
              <th>State</th>
              <th>Opened</th>
              <th>Last evaluated</th>
              <th>Acknowledged</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid="alert-row">
                <td>
                  {r.message}
                  <small>{r.id}</small>
                </td>
                <td>{r.severity}</td>
                <td>{r.status}</td>
                <td>{evidenceTime(r.first_triggered_at)}</td>
                <td>{evidenceTime(r.last_evaluated_at)}</td>
                <td>
                  {r.acknowledged_at ? evidenceTime(r.acknowledged_at) : "No"}
                </td>
                <td>
                  <button
                    disabled={
                      busy ||
                      r.status !== "OPEN" ||
                      !!r.acknowledged_at ||
                      !hasPermission(
                        user,
                        "alerts.acknowledge",
                        r.organization_id,
                      )
                    }
                    onClick={() => acknowledge(r)}
                  >
                    Acknowledge
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data ? (
          <p>Loading monitoring alerts…</p>
        ) : (
          !rows.length && <p>No matching alerts.</p>
        )}
      </section>
    </div>
  );
}
