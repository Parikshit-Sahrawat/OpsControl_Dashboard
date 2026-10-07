import { useEffect, useState } from "react";
import TopNav from "./components/TopNav";
import JobDetailsDrawer from "./components/JobDetailsDrawer";
import Overview from "./pages/Overview";
import ETLJobs from "./pages/ETLJobs";
import { jobs as initialJobs, jobDetails as initialDetails } from "./data/mockData";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export default function App() {
  const [active, setActive] = useState("Overview");
  const [jobs, setJobs] = useState(() => clone(initialJobs));
  const [details, setDetails] = useState(() => clone(initialDetails));
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const selected = jobs.find(job => job.id === selectedId) ?? null;

  useEffect(() => {
    const timer = window.setInterval(() => {
      // Production contract: replace this mock tick with GET /api/v1/etl/executions.
      setLoading(false);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  const refresh = () => {
    setError(null);
    setLoading(true);
    window.setTimeout(() => setLoading(false), 350);
  };

  const updateInvestigation = (jobId, next) => {
    setDetails(current => {
      const copy = clone(current);
      const detail = copy[jobId] ?? { investigation: { status: "NEW", operator: "Operator A", started: "—", notes: [], transitions: [] } };
      const previous = detail.investigation?.status ?? "NEW";
      detail.investigation = detail.investigation ?? { status: previous, operator: "Operator A", started: "—", notes: [], transitions: [] };
      detail.investigation.status = next;
      detail.investigation.transitions = [
        ...(detail.investigation.transitions ?? []),
        { previous, next, timestamp: new Date().toLocaleTimeString("en-IN", { hour12: false }) + " IST", operator: "Operator A" },
      ];
      copy[jobId] = detail;
      return copy;
    });
  };

  const addNote = async (jobId, text) => {
    setDetails(current => {
      const copy = clone(current);
      const detail = copy[jobId] ?? { investigation: { status: "NEW", operator: "Operator A", started: "—", notes: [], transitions: [] } };
      detail.investigation = detail.investigation ?? { status: "NEW", operator: "Operator A", started: "—", notes: [], transitions: [] };
      detail.investigation.notes = [
        ...(detail.investigation.notes ?? []),
        { timestamp: new Date().toLocaleTimeString("en-IN", { hour12: false }), operator: "Operator A", text },
      ];
      copy[jobId] = detail;
      return copy;
    });
  };

  return (
    <div className="app-shell">
      <TopNav active={active} onChange={page => { setActive(page); setSelectedId(null); }} />
      <main className="content">
        {active === "Overview" && <Overview jobs={jobs} onSelect={setSelectedId} />}
        {active === "ETL Jobs" && <ETLJobs jobs={jobs} loading={loading} error={error} onRetry={refresh} onSelect={setSelectedId} />}
        {!["Overview", "ETL Jobs"].includes(active) && <div className="card placeholder"><h1>{active}</h1><p>Page structure reserved for the next implementation stage.</p></div>}
      </main>
      <JobDetailsDrawer
        job={selected}
        details={selected ? details[selected.id] : null}
        onClose={() => setSelectedId(null)}
        onInvestigationChange={updateInvestigation}
        onAddNote={addNote}
      />
    </div>
  );
}