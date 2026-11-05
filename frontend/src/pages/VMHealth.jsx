import { useCallback, useEffect, useRef, useState } from "react";
import { authHeaders } from "../auth";
import { evidenceTime } from "../operations";
import StatusBadge from "../components/StatusBadge";
import InventoryPager from "../components/InventoryPager";
const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export default function VMHealth({
  organizationIds,
  environment = [],
  initialSourceId,
  embedded = false,
}) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(null),
    [history, setHistory] = useState([]);
  const [offset, setOffset] = useState(0),
    scope = organizationIds.join(",") + ":" + environment.join(",");
  useEffect(() => setOffset(0), [scope]);
  const generation = useRef(0);
  const requestController = useRef(null);
  const requestInFlight = useRef(false);
  const initialOpened = useRef(false);
  useEffect(() => {
    if (data && initialSourceId && !initialOpened.current) {
      initialOpened.current = true;
      setSelected(data.resources.find((r) => r.id === initialSourceId) || null);
    }
  }, [data, initialSourceId]);
  const [search, setSearch] = useState(""),
    [provider, setProvider] = useState("ALL"),
    [health, setHealth] = useState("ALL");
  const refresh = useCallback(async () => {
    if (requestInFlight.current || document.hidden) return;
    requestInFlight.current = true;
    const controller = new AbortController();
    requestController.current = controller;
    const requestGeneration = generation.current;
    try {
      const query = new URLSearchParams();
      organizationIds.forEach((id) => query.append("organization_id", id));
      environment.forEach((value) => query.append("environments", value));
      query.set("offset", offset);
      query.set("limit", "50");
      const response = await fetch(
        `${BASE}/api/v1/infrastructure/resources?${query}`,
        { headers: authHeaders(), signal: controller.signal },
      );
      if (!response.ok)
        throw new Error("Infrastructure health could not be loaded.");
      const next = await response.json();
      if (requestGeneration !== generation.current) return;
      setData(next);
      setError("");
      setSelected((current) =>
        current
          ? next.resources.find((r) => r.id === current.id) || null
          : null,
      );
    } catch (e) {
      if (requestGeneration !== generation.current) return;
      setError(e.message);
      setData(null);
      setSelected(null);
    } finally {
      requestInFlight.current = false;
      if (requestController.current === controller) requestController.current = null;
    }
  }, [organizationIds, environment, offset]);
  useEffect(() => {
    generation.current++;
    requestController.current?.abort();
    requestInFlight.current = false;
    setSelected(null);
    setHistory([]);
    setData(null);
    refresh();
    const timer = setInterval(refresh, 15000);
    return () => {
      generation.current++;
      requestController.current?.abort();
      clearInterval(timer);
    };
  }, [refresh]);
  useEffect(() => {
    let active = true;
    setHistory([]);
    if (!selected) return;
    fetch(`${BASE}/api/v1/infrastructure/resources/${selected.id}/history`, {
      headers: authHeaders(),
    })
      .then((r) => {
        if (!r.ok) throw new Error("Evidence history unavailable.");
        return r.json();
      })
      .then((rows) => {
        if (active) setHistory(rows);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected?.id, data]);
  const rows = (data?.resources || []).filter(
    (r) =>
      (provider === "ALL" || r.provider === provider) &&
      (health === "ALL" || r.health === health) &&
      r.name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="vm-health">
      <div className="page-heading">
        <div>
          {embedded ? (
            <h2>Infrastructure adapter health</h2>
          ) : (
            <h1>VM Health</h1>
          )}
          <p>
            Infrastructure evidence · AWS EC2 and host workers · refresh
            every 5 seconds
          </p>
        </div>
        <button onClick={refresh}>Refresh infrastructure</button>
      </div>
      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      <div className="kpi-grid">
        {["HEALTHY", "WARNING", "CRITICAL", "UNKNOWN", "DISABLED"].map(
          (status) => (
            <button
              key={status}
              className="card infrastructure-kpi"
              aria-pressed={health === status}
              onClick={() => setHealth(status)}
              aria-label={`Filter ${status}`}
            >
              <b>{status}</b>
              <p>{data?.summary[status] ?? "—"}</p>
            </button>
          ),
        )}
      </div>
      <section className="card">
        <div className="monitoring-setup-grid">
          <label>
            Search infrastructure
            <input value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
          <label>
            Provider
            <select
              aria-label="Provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="ALL">All providers</option>
              {[...new Set((data?.resources || []).map((r) => r.provider))].map(
                (p) => (
                  <option key={p}>{p}</option>
                ),
              )}
            </select>
          </label>
          <label>
            Health
            <select
              aria-label="Health"
              value={health}
              onChange={(e) => setHealth(e.target.value)}
            >
              {[
                "ALL",
                "HEALTHY",
                "WARNING",
                "CRITICAL",
                "UNKNOWN",
                "DISABLED",
              ].map((h) => (
                <option key={h}>{h}</option>
              ))}
            </select>
          </label>
        </div>
        {!data && !error && <p>Loading infrastructure…</p>}
        {data && (
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Provider</th>
                <th>Health</th>
                <th>Collector / freshness</th>
                <th>Latest metrics</th>
                <th>Open alerts</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-testid="infrastructure-row">
                  <td>
                    <button
                      className="text-link"
                      onClick={() => setSelected(r)}
                    >
                      {r.name}
                    </button>
                  </td>
                  <td>{r.provider}</td>
                  <td>
                    <StatusBadge status={r.health} />
                  </td>
                  <td>
                    {r.collectors.map((c) => (
                      <div key={c.id}>
                        {c.status} · {c.freshness}
                        {!c.enabled ? " · disabled" : ""}
                      </div>
                    ))}
                  </td>
                  <td>
                    {r.metrics.map((m, i) => (
                      <div key={i}>
                        {m.name}: {Number(m.value).toFixed(2)} {m.unit || ""}
                      </div>
                    ))}
                  </td>
                  <td>{r.open_alert_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {data && !rows.length && (
          <p>
            No infrastructure resources match this organization and filters.
          </p>
        )}
        {data?.truncated && (
          <p>
            Health counts and filters apply to the current page. Total inventory
            includes all authorized resources.
          </p>
        )}
        <InventoryPager data={data} onOffsetChange={setOffset} />
      </section>
      {selected && (
        <section className="card" data-testid="infrastructure-detail">
          <div className="section-heading-row">
            <h2>{selected.name}</h2>
            <button onClick={() => setSelected(null)}>Close resource</button>
          </div>
          <h3>Collector evidence</h3>
          {selected.collectors.map((c) => (
            <div key={c.id}>
              <p>
                {c.name} · {c.status} · {c.freshness}
              </p>
              {c.last_error && <p role="alert">{c.last_error}</p>}
              <pre>{JSON.stringify(c.evidence, null, 2)}</pre>
            </div>
          ))}
          <h3>Alerts</h3>
          {selected.alerts.length ? (
            selected.alerts.map((a) => (
              <p key={a.id}>
                {a.status} · {a.severity} · {a.message}
                {a.resolved_at
                  ? ` · resolved ${evidenceTime(a.resolved_at)}`
                  : ""}
              </p>
            ))
          ) : (
            <p>No alert history for this resource.</p>
          )}
          <h3>Operational history</h3>
          {history.length ? (
            <table>
              <thead>
                <tr>
                  <th>Observed (IST)</th>
                  <th>Provider</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                {history.map((e) => (
                  <tr key={e.id}>
                    <td>{evidenceTime(e.observed_at)}</td>
                    <td>{e.provider}</td>
                    <td>{e.payload.outcome || "UNKNOWN"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No collected evidence yet.</p>
          )}
        </section>
      )}
    </div>
  );
}
