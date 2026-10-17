import { useEffect, useState } from "react";
import { hasPermission } from "../permissions";
import usePipelineFeed from "./usePipelineFeed";
import { PAGES, params, nativeType, outcome, resourcePath } from "./contracts";
import {
  State,
  Status,
  Stamp,
  Identifier,
  Facts,
  Table,
  Pager,
  Drawer,
  Evidence,
} from "./ui";
import { ExecutionHistory } from "./ExecutionViews";
import ScheduleView from "./ScheduleView";
import ReviewView from "./ReviewView";
import RecoveryView from "./RecoveryView";
import IncidentView from "./IncidentView";
import "./pipelines.css";
const hashPage = () => {
  const key = window.location.hash.split("/")[2];
  return PAGES[key] ? key : "inventory";
};
export default function PipelineWorkspace({
  organizationIds,
  environment,
  user,
  initialResourceId,
}) {
  const [page, setPage] = useState(hashPage),
    [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [offset, setOffset] = useState(0),
    [resourceId, setResourceId] = useState(initialResourceId || ""),
    [drawer, setDrawer] = useState(null),
    [recoveryExecution, setRecoveryExecution] = useState(null),
    ids = organizationIds.filter((id) => hasPermission(user, "etl.view", id)),
    inventoryIds = ids.filter((id) =>
      hasPermission(user, "resources.view", id),
    );
  const feed = usePipelineFeed(
      inventoryIds.length
        ? "/api/v1/unified/resources?" +
            params(inventoryIds, environment, {
              domain: "ETL",
              search: query,
              limit: 20,
              offset,
            })
        : null,
      true,
    ),
    chosen = usePipelineFeed(
      inventoryIds.length && resourceId ? resourcePath(resourceId) : null,
    );
  const resource =
    chosen.data &&
    inventoryIds.includes(chosen.data.organization_id) &&
    (!environment || chosen.data.environment === environment)
      ? {
          ...chosen.data,
          binding: feed.data?.items.find((r) => r.id === resourceId)?.binding,
        }
      : null;
  useEffect(() => {
    const handle = () => setPage(hashPage());
    window.addEventListener("hashchange", handle);
    return () => window.removeEventListener("hashchange", handle);
  }, []);
  useEffect(() => {
    if (!resourceId && feed.data?.items.length)
      setResourceId(feed.data.items[0].id);
  }, [feed.data, resourceId]);
  const navigate = (key) => {
    setPage(key);
    window.location.hash = "/pipelines/" + key;
    setDrawer(null);
  };
  if (!ids.length)
    return (
      <section className="pipeline-workspace">
        <h1>Data Pipeline Monitoring</h1>
        <p role="status">
          Select a customer with etl.view permission. Monitoring requests
          require an authorized customer scope.
        </p>
      </section>
    );
  return (
    <section
      className="pipeline-workspace"
      aria-label="Data Pipeline operational workspace"
    >
      <div className="page-heading">
        <div>
          <p className="pipeline-eyebrow">DATA PIPELINES / OPERATIONS</p>
          <h1>{PAGES[page]}</h1>
          <p>
            Native evidence · execution, monitoring and incident states · UTC
          </p>
        </div>
        <button
          onClick={() => window.dispatchEvent(new Event("pipeline-refresh"))}
        >
          Refresh evidence
        </button>
      </div>
      <nav className="pipeline-tabs" aria-label="Pipeline operational pages">
        {Object.entries(PAGES).map(([key, name]) => (
          <a
            key={key}
            href={"#/pipelines/" + key}
            aria-current={page === key ? "page" : undefined}
            onClick={() => setDrawer(null)}
          >
            {name}
          </a>
        ))}
      </nav>
      {ids.length !== organizationIds.length && (
        <p role="status">
          Showing only selected customers with etl.view. Multiple selections do
          not grant ALL access.
        </p>
      )}
      {page !== "incidents" && inventoryIds.length === 0 && (
        <p role="status">
          Resource discovery requires resources.view as well as etl.view for the
          selected customer. Request the existing read grants from an access
          administrator.
        </p>
      )}
      {page !== "incidents" && inventoryIds.length > 0 && (
        <>
          <form
            className="pipeline-filters"
            onSubmit={(e) => {
              e.preventDefault();
              setQuery(search);
              setOffset(0);
            }}
          >
            <label>
              Find pipeline
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search monitored pipeline names"
              />
            </label>
            <button type="submit">Search pipelines</button>
            {page !== "inventory" && (
              <label>
                Selected pipeline
                <select
                  value={resourceId}
                  onChange={(e) => {
                    setResourceId(e.target.value);
                    setRecoveryExecution(null);
                  }}
                >
                  <option value="">Choose pipeline</option>
                  {resource &&
                    !feed.data?.items.some((r) => r.id === resource.id) && (
                      <option value={resource.id}>{resource.name}</option>
                    )}
                  {feed.data?.items.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} · {r.inherited?.customer || r.organization_id} ·{" "}
                      {r.environment}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </form>
          <State feed={feed} empty={!feed.data?.items.length} />
          {page === "inventory" && (
            <>
              <p className="muted">
                Collection availability and verified native capability are
                reported separately.
              </p>
              <Table
                label="Pipeline inventory"
                headers={[
                  "Pipeline / native type",
                  "Customer / environment",
                  "Source / method",
                  "Collection / monitoring",
                  "Last observation (UTC)",
                  "Last execution / outcome",
                  "Completeness / capability",
                ]}
              >
                {feed.data?.items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <button
                        onClick={() => {
                          setResourceId(r.id);
                          setDrawer(r);
                        }}
                      >
                        {r.name}
                      </button>
                      <small>
                        {r.configuration?.platform || "Platform unreported"} ·{" "}
                        {nativeType(r)}
                      </small>
                    </td>
                    <td>
                      {r.inherited?.customer || r.organization_id}
                      <small>{r.environment}</small>
                    </td>
                    <td>
                      <Identifier
                        value={r.primary_collector_id || r.data_source_id}
                      />
                      <small>
                        {r.binding?.sources
                          .map((s) => s.method_type)
                          .join(", ") || "Method unreported"}
                      </small>
                    </td>
                    <td>
                      {r.binding?.sources.map((s) => s.health).join(", ") ||
                        r.activation_status}
                      <small>
                        {r.observationUnavailable
                          ? "Evidence unavailable"
                          : r.source_verification?.ready === true
                            ? "Monitoring checks passed"
                            : r.source_verification?.reason ||
                              "Monitoring unverified"}
                      </small>
                    </td>
                    <td>
                      <Stamp
                        value={
                          r.source_verification?.last_received_at ||
                          r.latest_execution?.source_evidence?.observed_at
                        }
                      />
                    </td>
                    <td>
                      <Identifier value={r.latest_execution?.id} />
                      <small>
                        <Status value={outcome(r.latest_execution || {})} />
                      </small>
                    </td>
                    <td>
                      <Status
                        value={
                          r.latest_execution?.pentaho_completeness || "UNKNOWN"
                        }
                      />
                      <small>
                        Capability:{" "}
                        {r.binding?.capabilities
                          .map((c) => c.evidence_status)
                          .join(", ") || "Unverified"}
                      </small>
                      {r.bindingUnavailable && (
                        <small>Capability evidence unavailable</small>
                      )}
                    </td>
                  </tr>
                ))}
              </Table>
            </>
          )}
          <Pager
            total={feed.data?.total}
            offset={offset}
            onChange={setOffset}
            label="Pipelines"
          />
          {page !== "inventory" && (
            <>
              <State feed={chosen} />
              {!resource && !chosen.loading && (
                <p>Select an authorized pipeline.</p>
              )}
              {resource && (
                <div key={resource.id + page} className="pipeline-section">
                  <div className="pipeline-scope">
                    <strong>{resource.name}</strong>
                    <span>
                      {resource.inherited?.customer || resource.organization_id}{" "}
                      · {resource.environment} · {nativeType(resource)}
                    </span>
                  </div>
                  {page === "executions" && (
                    <ExecutionHistory
                      resource={resource}
                      user={user}
                      onRecovery={(h) => {
                        setRecoveryExecution(h);
                        navigate("recovery");
                      }}
                    />
                  )}
                  {page === "schedules" && <ScheduleView resource={resource} />}
                  {page === "evidence" &&
                    (resource.configuration?.platform === "PENTAHO" ? (
                      <ReviewView resource={resource} user={user} />
                    ) : (
                      <p>
                        Canonical identity adjudication is not exposed for this
                        platform. Execution evidence remains available.
                      </p>
                    ))}
                  {page === "recovery" && (
                    <RecoveryView
                      resource={resource}
                      user={user}
                      initialExecution={recoveryExecution}
                    />
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}
      {page === "incidents" && (
        <IncidentView
          organizationIds={ids}
          environment={environment}
          user={user}
        />
      )}
      {drawer && (
        <Drawer
          title="Pipeline operational details"
          onClose={() => setDrawer(null)}
        >
          <h3>{drawer.name}</h3>
          <Facts
            items={{
              Platform: drawer.configuration?.platform,
              "Native type": nativeType(drawer),
              Customer: drawer.inherited?.customer,
              Environment: drawer.environment,
              "Resource ID": <Identifier value={drawer.id} />,
              Collector: <Identifier value={drawer.primary_collector_id} />,
              Collection: drawer.activation_status,
              "Monitoring health": drawer.source_verification?.ready
                ? "Checks passed"
                : "Unverified",
            }}
          />
          <nav className="pipeline-tabs" aria-label="Pipeline detail sections">
            {Object.entries(PAGES)
              .filter(([key]) => key !== "inventory")
              .map(([key, name]) => (
                <button key={key} onClick={() => navigate(key)}>
                  {name}
                </button>
              ))}
          </nav>
          <h3>Source and monitoring checks</h3>
          <Evidence value={drawer.source_verification} />
          <PipelineBindings resource={drawer} />
        </Drawer>
      )}
    </section>
  );
}
function PipelineBindings({ resource }) {
  const id = resource.configuration?.pipeline_integration_id,
    feed = usePipelineFeed(
      id ? "/api/v1/data-pipelines/integrations/" + id : null,
    );
  return (
    <>
      <h3>Collection bindings and capability evidence</h3>
      <State feed={feed} />
      {!id ? (
        <p>
          No integration binding is exposed. Capability certification is not
          inferred.
        </p>
      ) : (
        <>
          <Table
            label="Collection methods"
            headers={["Method", "Transport", "Source", "Capability"]}
          >
            {feed.data?.methods.map((m) => (
              <tr key={m.id}>
                <td>
                  {m.configuration?.method_type ||
                    feed.data?.sources.find((s) => s.id === m.source_id)
                      ?.method_type ||
                    "Unreported"}
                </td>
                <td>{m.transport}</td>
                <td>
                  <Identifier value={m.source_id} />
                </td>
                <td>
                  <Identifier value={m.capability_id} />
                </td>
              </tr>
            ))}
          </Table>
          {feed.data?.capabilities.map((c) => (
            <Facts
              key={c.id}
              items={{
                "Exact build": c.platform_version,
                Verification: c.evidence_status,
                Edition: c.edition,
                "Capability ID": <Identifier value={c.id} />,
              }}
            />
          ))}
          <p>
            Documented support and controlled fixtures do not certify an
            installed runtime.
          </p>
        </>
      )}
    </>
  );
}
