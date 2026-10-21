import { useEffect, useState } from "react";
import {
  operations,
  useOperationalFeed,
  scopeQuery,
  evidenceTime,
} from "../operations";
import EvidenceDrawer from "../components/EvidenceDrawer";
import InventoryPager from "../components/InventoryPager";
import StatusBadge from "../components/StatusBadge";

export default function APIs({
  organizationIds,
  environment = [],
  initialSourceId,
  onNavigate,
  embedded = false,
}) {
  const [offset, setOffset] = useState(0),
    scope = organizationIds.join(",") + ":" + environment.join(",");
  useEffect(() => setOffset(0), [scope]);
  const { data, error, refresh } = useOperationalFeed(
    "/services?" + scopeQuery(organizationIds, { offset }) + environment.map((value) => "&environments=" + encodeURIComponent(value)).join(""),
  );
  const [health, setHealth] = useState("ALL"),
    [search, setSearch] = useState(""),
    [id, setId] = useState(initialSourceId || null),
    [detail, setDetail] = useState(null),
    [detailError, setDetailError] = useState("");
  useEffect(() => {
    setId(initialSourceId || null);
  }, [initialSourceId]);
  useEffect(() => {
    let live = true;
    setDetail(null);
    setDetailError("");
    if (id)
      operations("/services/" + id)
        .then((value) => {
          if (live) setDetail(value);
        })
        .catch((e) => {
          if (live) setDetailError(e.message);
        });
    return () => {
      live = false;
    };
  }, [id, data]);
  const rows = (data?.services || []).filter(
    (row) =>
      (health === "ALL" || row.health === health) &&
      row.name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="operations-page">
      <div className="page-heading">
        <div>
          {embedded ? (
            <h2>Existing service probes</h2>
          ) : (
            <h1>API Monitoring</h1>
          )}
          <p>
            HTTP service health from stored collector runs · refresh every 5
            seconds
          </p>
        </div>
        <button onClick={refresh}>Refresh services</button>
      </div>
      {error && <p role="alert">{error}</p>}
      <div className="kpi-grid">
        {["HEALTHY", "CRITICAL", "UNKNOWN", "DISABLED"].map((state) => (
          <button
            className="card operational-kpi"
            key={state}
            aria-pressed={health === state}
            onClick={() => setHealth(state)}
          >
            <b>{state}</b>
            <p>{data?.summary[state] ?? "—"}</p>
          </button>
        ))}
      </div>
      <section className="card">
        <div className="operational-filters">
          <label>
            Search services
            <input value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
          <label>
            Service health
            <select value={health} onChange={(e) => setHealth(e.target.value)}>
              {["ALL", "HEALTHY", "CRITICAL", "UNKNOWN", "DISABLED"].map(
                (state) => (
                  <option key={state}>{state}</option>
                ),
              )}
            </select>
          </label>
        </div>
        {!data && !error && <p>Loading service evidence…</p>}
        {data?.truncated && (
          <p>
            Health counts and filters cover the current page; total inventory
            includes every authorized service.
          </p>
        )}
        <table>
          <thead>
            <tr>
              <th>Service</th>
              <th>Health</th>
              <th>Collector / freshness</th>
              <th>HTTP status</th>
              <th>Response time</th>
              <th>Open alerts</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} data-testid="service-row">
                <td>
                  <button className="text-link" onClick={() => setId(row.id)}>
                    {row.name}
                  </button>
                </td>
                <td>
                  <StatusBadge status={row.health} />
                </td>
                <td>
                  {row.collectors.map((c) => (
                    <div key={c.id}>
                      {c.status} · {c.freshness}
                    </div>
                  ))}
                </td>
                <td>
                  {row.collectors.map((c) => (
                    <div key={c.id}>{c.latest_run?.http_status ?? "—"}</div>
                  ))}
                </td>
                <td>
                  {row.collectors.map((c) => (
                    <div key={c.id}>
                      {c.latest_run?.response_time_ms != null
                        ? c.latest_run.response_time_ms + " ms"
                        : "—"}
                    </div>
                  ))}
                </td>
                <td>{row.open_alert_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && !rows.length && (
          <p>No services match this organization and filters.</p>
        )}
        <InventoryPager data={data} onOffsetChange={setOffset} />
      </section>
      {id && (
        <EvidenceDrawer
          title={detail?.name || "Service evidence"}
          onClose={() => setId(null)}
        >
          {detailError && <p role="alert">{detailError}</p>}
          {!detail && !detailError && <p>Loading evidence…</p>}
          {detail && (
            <>
              <p>
                Health: <b>{detail.health}</b>
              </p>
              <h3>Collector evidence</h3>
              {detail.collectors.map((c) => (
                <p key={c.id}>
                  {c.name} · {c.status} · {c.freshness}
                  <br />
                  Observed: {evidenceTime(c.latest_run?.observed_at)}
                </p>
              ))}
              <h3>Alert lifecycle</h3>
              {detail.alerts.map((a) => (
                <div className="evidence-event" key={a.id}>
                  <b>
                    {a.status} · {a.severity}
                  </b>
                  <p>{a.message}</p>
                  <small>
                    Opened {evidenceTime(a.opened_at)} · Resolved{" "}
                    {evidenceTime(a.resolved_at)}
                  </small>
                </div>
              ))}
              {!detail.alerts.length && <p>No alert evidence yet.</p>}
              <button onClick={() => onNavigate("Alerts")}>Open alerts</button>
              <h3>Operational history</h3>
              <table>
                <thead>
                  <tr>
                    <th>Observed</th>
                    <th>Result</th>
                    <th>HTTP</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.history.map((run) => (
                    <tr key={run.id}>
                      <td>{evidenceTime(run.observed_at)}</td>
                      <td>
                        {run.status}
                        <small>{run.outcome}</small>
                      </td>
                      <td>{run.http_status ?? "—"}</td>
                      <td>
                        {run.response_time_ms != null
                          ? run.response_time_ms + " ms"
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!detail.history.length && <p>No collected runs yet.</p>}
            </>
          )}
        </EvidenceDrawer>
      )}
    </div>
  );
}
