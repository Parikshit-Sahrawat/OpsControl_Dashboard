import { useState } from "react";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
import { query, useNativeFeed } from "./UnifiedOverview";
export default function Alerts({
  organizationIds,
  environment,
  user,
  initialFilter = {},
}) {
  const [filter, setFilter] = useState(initialFilter.status || "ALL"),
    [search, setSearch] = useState(""),
    [domain, setDomain] = useState(initialFilter.domain || ""),
    [offset, setOffset] = useState(0),
    [failure, setFailure] = useState(""),
    [busy, setBusy] = useState(false),
    [correlations, setCorrelations] = useState(
      Boolean(initialFilter.correlations),
    );
  const args = {
    limit: 100,
    offset,
    ...(domain ? { domain } : {}),
    ...(filter !== "ALL" ? { status: filter } : {}),
    ...(initialFilter.resourceId
      ? { resource_id: initialFilter.resourceId }
      : {}),
  };
  const feed = useNativeFeed(
    "/api/v1/unified/alerts?" + query(organizationIds, environment, args),
  );
  const groups = useNativeFeed(
    "/api/v1/unified/correlations?" +
      query(organizationIds, environment, { limit: 100 }),
  );
  const acknowledge = async (row) => {
    if (
      !confirm(
        "Acknowledge this alert? Resolution still requires recovery evidence.",
      )
    )
      return;
    setBusy(true);
    try {
      await control(
        "/api/v1/operations/alerts/" + row.id + "/acknowledge",
        "POST",
      );
      feed.refresh();
    } catch (e) {
      setFailure(e.message);
    } finally {
      setBusy(false);
    }
  };
  const rows = (feed.data?.alerts || []).filter(
    (a) =>
      (!initialFilter.alertId || a.id === initialFilter.alertId) &&
      (a.message + " " + a.resource_name)
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <div className="operations-page">
      <div className="page-heading">
        <h1>Alerts</h1>
        <button
          onClick={() => {
            feed.refresh();
            groups.refresh();
          }}
        >
          Refresh
        </button>
      </div>
      <div className="heading-actions">
        <button onClick={() => setCorrelations(false)}>
          Monitoring alerts
        </button>
        <button onClick={() => setCorrelations(true)}>Correlated Events</button>
      </div>
      {(feed.error || groups.error || failure) && (
        <p role="alert" className="error-banner">
          {failure || feed.error || groups.error}
        </p>
      )}
      {!correlations && (
        <>
          <div className="resource-toolbar">
            <input
              aria-label="Search alerts"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              aria-label="Alert status"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                setOffset(0);
              }}
            >
              <option>ALL</option>
              <option>OPEN</option>
              <option>RESOLVED</option>
            </select>
            <select
              aria-label="Alert domain"
              value={domain}
              onChange={(e) => {
                setDomain(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All monitoring domains</option>
              <option>ETL</option>
              <option>VM</option>
              <option>API</option>
            </select>
          </div>
          <section className="card table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Resource / domain</th>
                  <th>Alert evidence</th>
                  <th>Severity</th>
                  <th>State</th>
                  <th>Opened / evaluated</th>
                  <th>Acknowledgment</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} data-testid="alert-row">
                    <td>
                      {row.resource_name}
                      <small>
                        {row.domain} · {row.environment || "Unmapped"}
                      </small>
                    </td>
                    <td>
                      {row.message}
                      <small>{row.rule_name || "Unmapped rule"}</small>
                      <small>{row.id}</small>
                    </td>
                    <td>{row.severity}</td>
                    <td>{row.status}</td>
                    <td>
                      {row.first_triggered_at}
                      <small>{row.last_evaluated_at}</small>
                    </td>
                    <td>
                      {row.acknowledged_at ? (
                        "Acknowledged " + row.acknowledged_at
                      ) : (
                        <button
                          disabled={
                            busy ||
                            !hasPermission(
                              user,
                              "alerts.acknowledge",
                              row.organization_id,
                            )
                          }
                          onClick={() => acknowledge(row)}
                        >
                          Acknowledge
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {feed.data && !rows.length && (
              <p>No alerts match these scoped filters.</p>
            )}
          </section>
          {feed.data && (
            <div className="form-footer">
              <span>{feed.data.total} alerts</span>
              <button
                disabled={!offset}
                onClick={() => setOffset((v) => Math.max(0, v - 100))}
              >
                Previous
              </button>
              <button
                disabled={!feed.data.has_more}
                onClick={() => setOffset((v) => v + 100)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
      {correlations && (
        <section className="card table-wrap">
          <h2>Correlated Events</h2>
          <table>
            <thead>
              <tr>
                <th>Group ID</th>
                <th>Relationship-supported conditions</th>
                <th>Confidence</th>
                <th>State</th>
                <th>Evidence / members</th>
              </tr>
            </thead>
            <tbody>
              {groups.data?.items
                .filter(
                  (g) =>
                    !initialFilter.groupId || g.id === initialFilter.groupId,
                )
                .map((g) => (
                  <tr key={g.id}>
                    <td>{g.id}</td>
                    <td>{g.title}</td>
                    <td>{g.confidence}</td>
                    <td>{g.status}</td>
                    <td>
                      <details>
                        <summary>View supporting evidence</summary>
                        <pre>
                          {JSON.stringify(
                            { evidence: g.evidence, members: g.members },
                            null,
                            2,
                          )}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          {groups.data && !groups.data.items.length && (
            <p>No relationship-supported correlation groups.</p>
          )}
          <p className="muted">
            Correlation proposes a potential common cause. Temporal proximity
            alone does not prove root cause.
          </p>
        </section>
      )}
    </div>
  );
}
