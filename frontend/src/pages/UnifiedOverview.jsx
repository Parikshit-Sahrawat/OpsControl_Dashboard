import { useEffect, useState } from "react";
import WorldClock from "../components/WorldClock";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
export const query = (ids, environment, extra = {}) => {
  const q = new URLSearchParams(extra);
  ids.forEach((id) => q.append("organization_id", id));
  if (Array.isArray(environment)) environment.forEach((value) => q.append("environments", value));
  else if (environment) q.set("environment", environment);
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
    let timer;
    const request = async () => {
      if (!live || document.hidden) { if (live) timer = setTimeout(request, 15000); return; }
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
        if (live) timer = setTimeout(request, 15000);
      }
    };
    setData(null);
    request();
    return () => {
      live = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, tick]);
  return { data, error, refresh: () => setTick((v) => v + 1) };
}
export default function UnifiedOverview({
  organizationIds,
  organizations = [],
  environment,
  user,
  jobs = [],
  jobsLoading = false,
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
          <h1>Dashboard</h1>
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
      {hasPermission(user, "etl.view") && (
        <section className="card table-wrap">
          <h2>Running Data Pipeline Executions</h2>
          <p className="muted">Latest observed executions in the selected customer scope. A running state is execution evidence, not proof of source health.</p>
          <table>
            <thead><tr><th>Job / workflow</th><th>Customer</th><th>Host</th><th>Started (UTC)</th><th>Duration</th><th>State</th><th>Monitoring evidence</th></tr></thead>
            <tbody>
              {jobs.filter((job) => ["RUNNING", "LONG_RUNNING"].includes(job.status)).map((job) => (
                <tr key={job.id}>
                  <td><button onClick={() => onSelectExecution?.(job.id)}>{job.name}</button></td>
                  <td>{job.organization || "Unknown"}</td>
                  <td>{job.server || "Unknown"}</td>
                  <td>{job.startedAt ? new Date(job.startedAt).toLocaleString("en-GB", { timeZone: "UTC" }) : "Unknown"}</td>
                  <td>{job.duration || "Unknown"}</td>
                  <td>{job.status}</td>
                  <td>{job.monitoringStatus || "UNKNOWN"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!jobsLoading && !jobs.some((job) => ["RUNNING", "LONG_RUNNING"].includes(job.status)) && <p>No running execution in the latest bounded observation. This does not establish schedule compliance.</p>}
          {jobsLoading && <p>Loading execution evidence…</p>}
        </section>
      )}
      <div className="overview-companions">
        {["ETL", "VM", "API"].map((domain) => (
          <section key={domain} className="card table-wrap">
            <h2>
              {domain === "ETL"
                ? "Data Pipeline Alerts"
                : domain === "VM"
                  ? "Compute Health Alerts"
                  : "API Endpoint Alerts"}
            </h2>
            <p className="muted">Current open conditions from the latest bounded alert feed.</p>
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Resource</th>
                  <th>Condition</th>
                  <th>Severity</th>
                  <th>Started (UTC)</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {data?.alerts
                  .filter((a) => a.domain === domain && a.status === "OPEN")
                  .sort((a, b) =>
                    ({ CRITICAL: 0, HIGH: 1, WARNING: 2, MEDIUM: 3, LOW: 4 }[a.severity] ?? 5) -
                    ({ CRITICAL: 0, HIGH: 1, WARNING: 2, MEDIUM: 3, LOW: 4 }[b.severity] ?? 5) ||
                    (b.first_triggered_at || "").localeCompare(a.first_triggered_at || ""),
                  )
                  .map((a) => (
                    <tr key={a.id}>
                      <td>{organizations.find((org) => org.id === a.organization_id)?.name || "Unknown"}</td>
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
                      <td>{a.first_triggered_at ? new Date(a.first_triggered_at).toLocaleString("en-GB", { timeZone: "UTC" }) : "Unknown"}</td>
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
