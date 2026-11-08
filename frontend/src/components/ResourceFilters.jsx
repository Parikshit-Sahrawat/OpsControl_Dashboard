import { useState } from "react";
import { ENVIRONMENTS } from "../workspaceFilters";
export default function ResourceFilters({ customers, customer, environment, search, active, onChange, onApply, total, busy }) {
  const [advanced, setAdvanced] = useState(false);
  const field = (name, value) => onChange(name, value);
  return <section className="workspace-filters card" aria-label="Resource quick filters" aria-describedby="resource-filter-help">
    <div className="workspace-filter-heading"><h2>Quick filters</h2><span role="status">{busy ? "Updating matches…" : `${total ?? 0} matching resources`}</span></div>
    <div className="workspace-filter-grid">
      <label className="form-field"><span>Customer</span><select aria-label="Resource customer filter" value={customer} onChange={e => field("customer", e.target.value)}>
        <option value="">All authorized customers</option>
        {customer && !customers.some(c => c.id === customer) && <option value={customer}>Unavailable customer</option>}
        {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select></label>
      <label className="form-field"><span>Environment</span><select aria-label="Resource environment filter" value={environment} onChange={e => field("environment", e.target.value)}>
        <option value="">All environments</option>{ENVIRONMENTS.map(v => <option key={v}>{v}</option>)}
      </select></label>
      <label className="form-field workspace-filter-search"><span>Resource name</span><input aria-label="Search resources" type="search" maxLength={200} value={search} onChange={e => field("search", e.target.value)} placeholder="Search resource names…" /></label>
      <button type="button" onClick={() => setAdvanced(v => !v)} aria-expanded={advanced} aria-controls="resource-advanced-filters">Advanced filters</button>
      <button type="button" onClick={() => onChange("reset", "")}>Reset filters</button><button className="primary-button" type="button" onClick={onApply}>Apply filters</button>
    </div>
    {advanced && <div id="resource-advanced-filters" className="workspace-advanced-filters">
      <label className="form-field"><span>Configuration state</span><select aria-label="Configuration state filter" value={active} onChange={e => field("active", e.target.value)}><option value="">All configurations</option><option value="true">Enabled</option><option value="false">Disabled</option></select></label>
      <p className="muted">Configuration state does not establish monitoring health. Process, service, time-range and freshness filters will be available with their qualified monitoring views.</p>
    </div>}
    <div className="workspace-filter-footer"><div className="filter-chip-list" aria-label="Applied resource filters">
      {[["customer", customer && (customers.find(c => c.id === customer)?.name || "Unavailable customer")], ["environment", environment], ["search", search], ["active", active && (active === "true" ? "Enabled" : "Disabled")]].filter(([,v]) => v).map(([name,label]) => <button type="button" className="filter-chip" key={name} aria-label={`Remove ${name} filter`} onClick={() => field(name, "")}>{label} <span aria-hidden="true">×</span></button>)}
    </div></div>
    <p id="resource-filter-help" className="sr-only">Filters update the authorized inventory as you change them. Apply refreshes the same selection. The URL preserves these filters; it never grants access or stores credentials.</p>
  </section>;
}
