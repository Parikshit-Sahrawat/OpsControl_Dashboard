import { useEffect, useRef, useState } from "react";
import { canNavigate, administrationPage } from "../permissions";
import ThemeToggle from "./ThemeToggle";
import NavIcon from "./NavIcon";

const items = ["Overview", "ETL Jobs", "VM Health", "APIs", "Incidents", "Reports", "Resource Management", "Monitoring Setup"];

export default function TopNav({ active, onChange, organizations = [], organizationIds = [], onOrganizationChange, platformAdmin = false, user }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => setOpen(false), [active, user?.authorization_revision]);

  useEffect(() => {
    const close = event => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const allSelected = organizations.length > 0 && organizationIds.length === organizations.length;
  const label = allSelected
    ? "All customers"
    : organizationIds.length === 1
      ? (organizations.find(o => o.id === organizationIds[0])?.name || "1 customer")
      : `${organizationIds.length} customers`;

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
      <div className="brand">
        <button className="brand-link" onClick={() => onChange("Overview")} aria-label="Go to Overview">
          <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3 12h4l3-7 4 14 3-7h4"/></svg></span><span>OpsControl<span className="brand-caption">MONITORING WORKSPACE</span></span>
        </button>
      </div>
      <div className="workspace-breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><b>{active}</b></div>
      <nav aria-label="Primary navigation">
        <span className="nav-section-label">WORKSPACE</span>
        {[...items, "Access Management"].filter(item => canNavigate(user,item)).map(item => (
          <button key={item} aria-current={active === item ? "page" : undefined} className={active === item ? "nav-button active" : "nav-button"} onClick={() => onChange(item)}>
            <NavIcon name={item}/><span>{item}</span>
          </button>
        ))}
        <div className="sidebar-footnote"><span className="sidebar-footnote-mark" aria-hidden="true">◈</span><b>Your operations.<br/>One clear view.</b><small>Health · Evidence · Investigation</small></div>
      </nav>
      {administrationPage(active) ? <div className="global-context" aria-label="Administration context"><span className="muted">{active === "Access Management" ? "Service provider · internal access" : "Customer inventory · independent filters"}</span></div> : <div className="global-context" ref={ref}>
        <span className="context-label">Customer</span>
        <button disabled={!organizations.length} className={open ? "org-context-button open" : "org-context-button"} onClick={() => setOpen(value => !value)} aria-haspopup="true" aria-expanded={open}>
          <span className="org-context-label">{label}</span>
          <span className="org-context-chevron">▾</span>
        </button>
        {open && (
          <div className="org-menu">
            <label className="org-option org-option-all">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              <span><b>All customers</b><small>Select every authorized customer</small></span>
            </label>
            <div className="org-menu-divider" />
            {organizations.map(org => (
              <label className="org-option" key={org.id}>
                <input type="checkbox" checked={organizationIds.includes(org.id)} onChange={() => toggleOrganization(org.id)} />
                <span><b>{org.name}</b><small>{org.code}</small></span>
              </label>
            ))}
            {!organizations.length && <div className="org-empty">No authorized customers.</div>}
          </div>
        )}
      </div>}
      <ThemeToggle />
    </header>
  );
}
