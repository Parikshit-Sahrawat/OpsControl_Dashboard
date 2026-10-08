const items = ["Overview", "ETL Jobs", "VM Health", "APIs", "Incidents", "Reports", "Resource Management"];

export default function TopNav({ active, onChange, organizations = [], organizationId, onOrganizationChange }) {
  return (
    <header className="topbar">
      <div className="brand">OpsControl</div>
      <nav>
        {items.map((item) => (
          <button key={item} className={active === item ? "nav-button active" : "nav-button"} onClick={() => onChange(item)}>
            {item}
          </button>
        ))}
      </nav>
      <div className="global-context">
        <span className="context-label">Organization</span>
        <select className="global-org-select" value={organizationId || ""} onChange={e => onOrganizationChange(e.target.value)}>
          <option value="" disabled>Select organization</option>
          {organizations.map(org => <option key={org.id} value={org.id}>{org.name} ({org.code})</option>)}
        </select>
      </div>
    </header>
  );
}
