import {
  hasPermission,
  canNavigate,
  administrationPage,
  NAV_PERMISSIONS,
  parseCustomerSelection,
} from "./permissions";
import AccessManagement from "./pages/AccessManagement";
import Alerts from "./pages/Alerts";
import { useCallback, useEffect, useRef, useState } from "react";
import TopNav from "./components/TopNav";
import JobDetailsDrawer from "./components/JobDetailsDrawer";
import {
  fetchExecution,
  fetchExecutionEvidence,
  fetchExecutions,
  fetchInvestigation,
  transitionInvestigation,
  addInvestigationNote,
  mapExecution,
  fetchAuthorizedCustomers,
} from "./api";
import ResourceManagement from "./pages/UnifiedResourceManagement";
import NativeIncidents from "./pages/NativeIncidents";
import UnifiedOverview from "./pages/UnifiedOverview";
import DomainMonitoring from "./pages/DomainMonitoring";
import PipelineWorkspace from "./pipelines/PipelineWorkspace";
import DomainReports from "./pages/DomainReports";

function mapDetail(execution, investigation, evidence) {
  const fmt = (value) =>
    value
      ? new Date(value).toLocaleTimeString("en-IN", {
          hour12: false,
          timeZone: "Asia/Kolkata",
        })
      : "—";
  return {
    job: mapExecution(execution),
    organization: execution.organization,
    pentahoInstance: "—",
    detected: fmt(execution.detected_at) + " IST",
    lastUpdate: fmt(execution.source_evidence?.observed_at) + " IST",
    logs: evidence?.logs,
    sourceError: execution.source_error_message,
    monitoringStatus: execution.monitoring_status,
    providerExecutionId: execution.provider_execution_id,
    expectedWindow: [
      execution.source_evidence?.policy?.expected_window_start,
      execution.source_evidence?.policy?.expected_window_end,
    ]
      .filter(Boolean)
      .join(" – ")
      ? [
          execution.source_evidence?.policy?.expected_window_start,
          execution.source_evidence?.policy?.expected_window_end,
        ].join(" – ") +
        " (" +
        (execution.source_evidence?.policy?.timezone || "UTC") +
        ")"
      : execution.source_evidence?.deadline
        ? fmt(execution.source_evidence.deadline) + " IST"
        : undefined,
    gracePeriod:
      execution.source_evidence?.policy?.grace_seconds != null
        ? execution.source_evidence.policy.grace_seconds + "s"
        : undefined,
    slaStatus: execution.sla_status || "—",
    failureCategory: investigation?.failure_category,
    suspectedCause: investigation?.suspected_cause,
    confidence: investigation?.confidence,
    steps: (execution.steps || []).map((s) => ({
      name: s.name,
      status: s.status,
      type: s.step_type,
      duration:
        s.duration_seconds != null
          ? Math.floor(s.duration_seconds / 60) +
            "m " +
            String(s.duration_seconds % 60).padStart(2, "0") +
            "s"
          : null,
    })),
    timeline: (evidence?.timeline || []).map((item) => ({
      ...item,
      time: fmt(item.time) + " IST",
    })),
    alertHistory: (evidence?.alert_events || []).map((item) => ({
      time: fmt(item.timestamp) + " IST",
      event: item.event_type,
      reference: item.reference,
    })),
    recentHistory: (evidence?.history || [])
      .filter((item) => item.id !== execution.id)
      .map((item) => ({
        id: item.id,
        time: fmt(item.detected_at) + " IST",
        status: item.status,
        reason: item.provider_execution_id,
      })),
    investigation: investigation
      ? {
          status: investigation.status,
          operator: investigation.operator || "—",
          started: investigation.started_at
            ? fmt(investigation.started_at) + " IST"
            : "—",
          notes: (investigation.notes || []).map((n) => ({
            timestamp: fmt(n.timestamp),
            operator: n.operator,
            text: n.text,
          })),
          transitions: (investigation.transitions || []).map((t) => ({
            previous: t.previous_status,
            next: t.new_status,
            timestamp: fmt(t.timestamp) + " IST",
            operator: t.operator,
          })),
        }
      : undefined,
  };
}

export default function App({ user }) {
  const [active, setActive] = useState(() =>
      window.location.hash.startsWith("#/pipelines/") &&
      canNavigate(user, "Data Pipeline Monitoring")
        ? "Data Pipeline Monitoring"
        : Object.keys(NAV_PERMISSIONS).find((page) =>
            canNavigate(user, page),
          ) || "Unauthorized",
    ),
    [jobs, setJobs] = useState([]),
    [details, setDetails] = useState({}),
    [selectedId, setSelectedId] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [environment, setEnvironment] = useState(""),
    [customerRefresh, setCustomerRefresh] = useState(0);
  const [scopeReady, setScopeReady] = useState(false),
    [target, setTarget] = useState({});
  const generation = useRef(0);
  const [organizationIds, setOrganizationIds] = useState(() => {
    try {
      return parseCustomerSelection(
        window.localStorage.getItem("opscontrol.organizationIds"),
      );
    } catch {
      return [];
    }
  });
  const selected =
    jobs.find((job) => job.id === selectedId) ||
    details[selectedId]?.job ||
    null;
  const refresh = useCallback(async () => {
    if (
      !scopeReady ||
      !hasPermission(user, "etl.view") ||
      administrationPage(active) ||
      active === "Data Pipeline Monitoring"
    )
      return;
    const version = generation.current;
    try {
      const value = await fetchExecutions({
        latest_only: true,
        organization_ids: organizationIds,
        ...(environment ? { environment } : {}),
      });
      if (version === generation.current) {
        setError(null);
        setJobs(value);
      }
    } catch (e) {
      if (version === generation.current)
        setError(e.message || "Unable to load pipeline executions");
    } finally {
      if (version === generation.current) setLoading(false);
    }
  }, [
    organizationIds,
    scopeReady,
    active,
    user?.authorization_revision,
    environment,
  ]);
  useEffect(() => {
    let live = true;
    generation.current++;
    setScopeReady(false);
    setJobs([]);
    setDetails({});
    setSelectedId(null);
    setTarget({});
    if (!canNavigate(user, active))
      setActive(
        Object.keys(NAV_PERMISSIONS).find((page) => canNavigate(user, page)) ||
          "Unauthorized",
      );
    fetchAuthorizedCustomers()
      .then((orgs) => {
        if (!live) return;
        setOrganizations(orgs);
        const saved = (() => {
          try {
            return parseCustomerSelection(
              window.localStorage.getItem("opscontrol.organizationIds"),
            );
          } catch {
            return [];
          }
        })();
        const valid = saved.filter((id) => orgs.some((o) => o.id === id));
        setOrganizationIds(valid.length ? valid : orgs.map((o) => o.id));
        setScopeReady(true);
        setError(null);
      })
      .catch((e) => {
        if (live) {
          setOrganizations([]);
          setOrganizationIds([]);
          setScopeReady(true);
          setError(e.message);
        }
      });
    return () => {
      live = false;
      generation.current++;
    };
  }, [user?.authorization_revision, customerRefresh]);
  useEffect(() => {
    window.localStorage.setItem(
      "opscontrol.organizationIds",
      JSON.stringify(organizationIds),
    );
  }, [organizationIds]);
  const organizationId = organizationIds[0] || "";
  useEffect(() => {
    generation.current++;
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      generation.current++;
      window.clearInterval(timer);
    };
  }, [refresh]);
  const selectJob = async (job) => {
    if (!hasPermission(user, "etl.view")) return;
    const id = typeof job === "string" ? job : job.id,
      version = generation.current;
    setSelectedId(id);
    try {
      const execution = await fetchExecution(id);
      const evidence = await fetchExecutionEvidence(id);
      let investigation = null;
      try {
        investigation = await fetchInvestigation(id);
      } catch (e) {
        if (e.message !== "Investigation not found") throw e;
      }
      if (version === generation.current)
        setDetails((current) => ({
          ...current,
          [id]: mapDetail(execution, investigation, evidence),
        }));
    } catch (e) {
      if (version === generation.current)
        setError(e.message || "Unable to load execution details");
    }
  };
  useEffect(() => {
    if (selectedId) selectJob(selectedId);
  }, [jobs, selectedId]);
  const updateInvestigation = async (jobId, next) => {
    try {
      await transitionInvestigation(jobId, next);
      await selectJob(jobId);
    } catch (e) {
      setError(e.message || "Unable to update investigation");
    }
  };
  const addNote = async (jobId, text) => {
    try {
      await addInvestigationNote(jobId, text);
      await selectJob(jobId);
    } catch (e) {
      setError(e.message || "Unable to add note");
    }
  };
  useEffect(() => {
    const route = () => {
      if (
        window.location.hash.startsWith("#/pipelines/") &&
        canNavigate(user, "Data Pipeline Monitoring")
      )
        setActive("Data Pipeline Monitoring");
    };
    window.addEventListener("hashchange", route);
    return () => window.removeEventListener("hashchange", route);
  }, [user]);
  const navigate = (page, selection = {}) => {
    if (!canNavigate(user, page)) return;
    if (page === "Data Pipeline Monitoring")
      window.location.hash = "/pipelines/inventory";
    else if (window.location.hash.startsWith("#/pipelines/"))
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
    setTarget(selection);
    setActive(page);
    setSelectedId(null);
  };
  const openSource = (id, type) => {
    if (!hasPermission(user, "resources.view")) return;
    setSelectedId(null);
    setTarget({ sourceId: id });
    setActive(
      ["API", "HTTP", "HTTPS"].includes(type)
        ? "API Endpoint Monitoring"
        : "Compute Health",
    );
  };
  const openAlert = (id) => {
    if (!hasPermission(user, "alerts.view")) return;
    setSelectedId(null);
    setTarget({ incidentId: id });
    setActive("Alerts");
  };
  const scopeKey =
    (user?.authorization_revision || "") +
    organizationIds.join(",") +
    environment;
  return (
    <div className="app-shell">
      <TopNav
        active={active}
        onChange={navigate}
        environment={environment}
        onEnvironmentChange={(value) => {
          generation.current++;
          setJobs([]);
          setDetails({});
          setSelectedId(null);
          setTarget({});
          setLoading(true);
          setEnvironment(value);
        }}
        organizations={organizations}
        organizationIds={organizationIds}
        onOrganizationChange={(ids) => {
          generation.current++;
          setSelectedId(null);
          setDetails({});
          setJobs([]);
          setLoading(true);
          setTarget({});
          setOrganizationIds(ids);
        }}
        platformAdmin={user?.platform_admin}
        user={user}
      />
      <main className="content">
        {!scopeReady && <p>{error || "Loading authorized organizations…"}</p>}
        {scopeReady && error && active !== "Data Pipeline Monitoring" && (
          <p role="alert">{error}</p>
        )}
        {scopeReady && active === "Overview" && (
          <UnifiedOverview
            key={scopeKey}
            organizationIds={organizationIds}
            environment={environment}
            user={user}
            onNavigate={navigate}
            onSelectResource={(id, domain) =>
              navigate(
                domain === "ETL"
                  ? "Data Pipeline Monitoring"
                  : domain === "VM"
                    ? "Compute Health"
                    : "API Endpoint Monitoring",
                { resourceId: id },
              )
            }
          />
        )}
        {scopeReady && active === "Data Pipeline Monitoring" && (
          <PipelineWorkspace
            key={scopeKey + target.resourceId}
            user={user}
            organizationIds={organizationIds}
            environment={environment}
            initialResourceId={target.resourceId}
          />
        )}
        {active === "Access Management" &&
          hasPermission(user, "access.view") && (
            <AccessManagement key={user.authorization_revision} user={user} />
          )}
        {active === "Resource Management" && (
          <ResourceManagement
            key={user?.authorization_revision}
            user={user}
            onCustomerCreated={() => setCustomerRefresh((v) => v + 1)}
          />
        )}
        {scopeReady && active === "Compute Health" && (
          <DomainMonitoring
            key={scopeKey + target.resourceId}
            domain="VM"
            organizationIds={organizationIds}
            environment={environment}
            onNavigate={navigate}
            initialResourceId={target.resourceId}
          />
        )}
        {scopeReady && active === "API Endpoint Monitoring" && (
          <DomainMonitoring
            key={scopeKey + target.resourceId}
            domain="API"
            organizationIds={organizationIds}
            environment={environment}
            onNavigate={navigate}
            initialResourceId={target.resourceId}
          />
        )}
        {scopeReady && active === "Alerts" && (
          <Alerts
            key={scopeKey + JSON.stringify(target)}
            organizationIds={organizationIds}
            environment={environment}
            user={user}
            initialFilter={target}
          />
        )}
        {scopeReady && active === "Incidents" && (
          <NativeIncidents
            organizationIds={organizationIds}
            environment={environment}
            user={user}
          />
        )}
        {scopeReady && active === "Reports" && (
          <DomainReports
            key={scopeKey}
            organizationIds={organizationIds}
            environment={environment}
            onSelectExecution={selectJob}
          />
        )}
        {active === "Unauthorized" && (
          <section className="card state-panel">
            <h1>No assigned access</h1>
            <p>
              Ask your service-provider administrator for a role and explicit
              customer scope.
            </p>
          </section>
        )}
      </main>
      <JobDetailsDrawer
        job={selected}
        details={selected ? details[selected.id] : null}
        onClose={() => setSelectedId(null)}
        onInvestigationChange={updateInvestigation}
        onAddNote={addNote}
        onSelectExecution={selectJob}
        canInvestigate={
          Boolean(selected?.organizationId) &&
          hasPermission(user, "etl.investigate", selected.organizationId)
        }
      />
    </div>
  );
}
