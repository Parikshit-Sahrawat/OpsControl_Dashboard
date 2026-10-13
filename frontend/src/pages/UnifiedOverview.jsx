import { useEffect, useState } from "react";
import WorldClock from "../components/WorldClock";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
export const query = (ids, environment, extra = {}) => {
  const q = new URLSearchParams(extra);
  ids.forEach((id) => q.append("organization_id", id));
  if (environment) q.set("environment", environment);
  return q.toString();
};
export function useNativeFeed(path) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true,
      inFlight = false;
    const controller = new AbortController();
    const request = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const v = await control(path, "GET", undefined, {
          signal: controller.signal,
        });
        if (live) {
          setData(v);
          setError("");
        }
      } catch (e) {
        if (live && e.name !== "AbortError") setError(e.message);
      } finally {
        inFlight = false;
      }
    };
    setData(null);
    request();
    const timer = setInterval(request, 5000);
    return () => {
      live = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [path, tick]);
  return { data, error, refresh: () => setTick((v) => v + 1) };
}
const pages = { ETL: "ETL Monitoring", VM: "VM Health", API: "API Monitoring" };
export default function UnifiedOverview({
  organizationIds,
  environment,
  user,
  onNavigate,
  onSelectExecution,
  onSelectResource,
}) {
  const { data, error, refresh } = useNativeFeed(
    "/api/v1/unified/overview?" + query(organizationIds, environment),
  );
  return (
    <div className="unified-overview">
      <div className="page-heading">
        <div>
          <h1>Overview</h1>
          <p>Operational evidence across ETL, hosts and endpoints.</p>
        </div>
        <div className="overview-header-controls">
          <WorldClock />
          <button onClick={refresh}>Refresh</button>
        </div>
      </div>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!data && !error && <p>Loading scoped operational evidence…</p>}
      <section className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Monitoring domain</th>
              <th>Resources</th>
              <th>Monitoring active</th>
              <th>Open alerts</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data?.domains || {}).map(([domain, v]) => (
              <tr key={domain}>
                <td>
                  {domain === "ETL"
                    ? "ETL Monitoring"
                    : domain === "VM"
                      ? "VM Health"
                      : "API Monitoring"}
                </td>
                <td>
                  <button onClick={() => onNavigate(pages[domain])}>
                    {v.resources}
                  </button>
                </td>
                <td>{v.monitoring_active}</td>
                <td>
                  <button
                    disabled={!hasPermission(user, "alerts.view")}
                    onClick={() =>
                      onNavigate("Alerts", { domain, status: "OPEN" })
                    }
                  >
                    {v.open_alerts}
                  </button>
                </td>
                <td>
                  <button onClick={() => onNavigate(pages[domain])}>
                    View {domain.toLowerCase()} evidence
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <div className="overview-companions">
        {["ETL", "VM", "API"].map((domain) => (
          <section key={domain} className="card table-wrap">
            <h2>
              {domain === "ETL"
                ? "ETL Operational Alerts"
                : domain === "VM"
                  ? "VM Health Alerts"
                  : "API Operational Alerts"}
            </h2>
            <table>
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>Condition</th>
                  <th>Severity</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {data?.alerts
                  .filter((a) => a.domain === domain && a.status === "OPEN")
                  .map((a) => (
                    <tr key={a.id}>
                      <td>
                        <button
                          onClick={() =>
                            onSelectResource?.(a.resource_id, domain)
                          }
                        >
                          {a.resource_name}
                        </button>
                      </td>
                      <td>{a.message}</td>
                      <td>{a.severity}</td>
                      <td>
                        <button
                          onClick={() =>
                            onNavigate("Alerts", { domain, alertId: a.id })
                          }
                        >
                          {a.status}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {data &&
              !data.alerts.some(
                (a) => a.domain === domain && a.status === "OPEN",
              ) && <p>No open alerts in this authorized scope.</p>}
          </section>
        ))}
      </div>
      <section className="card table-wrap">
        <div className="page-heading">
          <h2>Correlated Events</h2>
          <button onClick={() => onNavigate("Alerts", { correlations: true })}>
            {data?.open_correlation_groups ?? "…"} open groups
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Correlation ID</th>
              <th>Related conditions</th>
              <th>Confidence</th>
              <th>State</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {data?.correlation_groups.map((g) => (
              <tr key={g.id}>
                <td>
                  <button
                    onClick={() =>
                      onNavigate("Alerts", {
                        correlations: true,
                        groupId: g.id,
                      })
                    }
                  >
                    {g.id}
                  </button>
                </td>
                <td>{g.title}</td>
                <td>{g.confidence}</td>
                <td>{g.status}</td>
                <td>
                  <details>
                    <summary>Relationship evidence</summary>
                    <pre>{JSON.stringify(g.evidence, null, 2)}</pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && !data.correlation_groups.length && (
          <p>No relationship-supported correlation groups.</p>
        )}
      </section>
      <p className="muted">{data?.measurement_note}</p>
    </div>
  );
}
