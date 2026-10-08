import { useEffect, useRef, useState } from "react";

const items = ["Overview", "ETL Jobs", "VM Health", "APIs", "Incidents", "Reports", "Resource Management"];

export default function TopNav({ active, onChange, organizations = [], organizationIds = [], onOrganizationChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const close = event => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const allSelected = organizations.length > 0 && organizationIds.length === organizations.length;
  const label = allSelected
    ? "All organizations"
    : organizationIds.length === 1
      ? (organizations.find(o => o.id === organizationIds[0])?.name || "1 organization")
      : `${organizationIds.length} organizations`;

  const toggleOrganization = id => {
    const next = organizationIds.includes(id)
      ? organizationIds.filter(value => value !== id)
      : [...organizationIds, id];
    if (next.length) onOrganizationChange(next);
  };

  const toggleAll = () => {
    onOrganizationChange(allSelected ? [organizations[0]?.id].filter(Boolean) : organizations.map(org => org.id));
  };

  return (
    <header className="topbar">
      <div className="brand">OpsControl</div>
      <nav>
        {items.map(item => (
          <button key={item} className={active === item ? "nav-button active" : "nav-button"} onClick={() => onChange(item)}>
            {item}
          </button>
        ))}
      </nav>
      <div className="global-context" ref={ref}>
        <span className="context-label">Organization</span>
        <button className={open ? "org-context-button open" : "org-context-button"} onClick={() => setOpen(value => !value)} aria-haspopup="true" aria-expanded={open}>
          <span className="org-context-label">{label}</span>
          <span className="org-context-chevron">▾</span>
        </button>
        {open && (
          <div className="org-menu">
            <label className="org-option org-option-all">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              <span><b>All organizations</b><small>Select every organization</small></span>
            </label>
            <div className="org-menu-divider" />
            {organizations.map(org => (
              <label className="org-option" key={org.id}>
                <input type="checkbox" checked={organizationIds.includes(org.id)} onChange={() => toggleOrganization(org.id)} />
                <span><b>{org.name}</b><small>{org.code}</small></span>
              </label>
            ))}
            {!organizations.length && <div className="org-empty">No organizations configured.</div>}
          </div>
        )}
      </div>
    </header>
  );
}
