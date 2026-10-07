import { useEffect, useState } from "react";
import TopNav from "./components/TopNav";
import JobDetailsDrawer from "./components/JobDetailsDrawer";
import Overview from "./pages/Overview";
import ETLJobs from "./pages/ETLJobs";
import { jobs, jobDetails } from "./data/mockData";

export default function App() {
  const [active, setActive] = useState("Overview");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const timer = window.setInterval(() => setActive(current => current), 5000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="app-shell">
      <TopNav active={active} onChange={(page) => { setActive(page); setSelected(null); }} />
      <main className="content">
        {active === "Overview" && <Overview jobs={jobs} onSelect={setSelected} />}
        {active === "ETL Jobs" && <ETLJobs jobs={jobs} onSelect={setSelected} />}
        {!["Overview", "ETL Jobs"].includes(active) && (
          <div className="card placeholder"><h1>{active}</h1><p>Page structure reserved for the next implementation stage.</p></div>
        )}
      </main>
      <JobDetailsDrawer job={selected} details={selected ? jobDetails[selected.id] : null} onClose={() => setSelected(null)} />
    </div>
  );
}