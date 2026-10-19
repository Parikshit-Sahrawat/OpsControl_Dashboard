import { useEffect, useRef, useState } from "react";
import { canNavigate, administrationPage } from "../permissions";
import { canOpenSection } from "../navigation";
import ThemeToggle from "./ThemeToggle";
import InAppNotifications from "./InAppNotifications";
import NavIcon from "./NavIcon";

// Labels describe the UI; keys remain the existing page identities and guards.
const sections = [
  { name: "Overview", items: [["Overview", "Dashboard"]] },
  { name: "Operations", items: [
    ["Data Pipeline Monitoring", "Data Pipelines"],
    ["Compute Health", "Compute Instances"],
    ["API Endpoint Monitoring", "API Endpoints"],
    ["Alerts", "Alerts"], ["Incidents", "Incidents"], ["Reports", "Reports"],
  ] },
  { name: "Resource Management", items: [
    ["Resource Management", "Organizations", "organizations"],
    ["Resource Management", "Data Sources / Resources", "resources"],
    ["Resource Management", "Collectors", "collectors"],
  ] },
  { name: "Access Management", items: [
    ["Access Management", "Employees", "Employees"],
    ["Access Management", "Departments", "Departments"],
    ["Access Management", "Roles & Permissions", "Roles & Permissions"],
    ["Access Management", "Organisational Access", "Organisational Access"],
    ["Access Management", "Access Audit", "Access Audit"],
  ] },
];

export default function TopNav({
  active,
  activeSection,
  onChange,
  organizations = [],
  organizationIds = [],
  onOrganizationChange,
  allCustomersAuthorized = false,
  allCustomersSelected = false,
  onAllCustomersChange,
  platformAdmin = false,
  user,
  environment = "",
  onEnvironmentChange,
}) {
  const [open, setOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileToggle = useRef(null);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("opscontrol.sidebarCollapsed") === "true",
  );
  useEffect(() => {
    document.documentElement.dataset.sidebar = collapsed
      ? "collapsed"
      : "expanded";
    localStorage.setItem("opscontrol.sidebarCollapsed", String(collapsed));
  }, [collapsed]);
  const ref = useRef(null);
  useEffect(() => {
    setOpen(false);
    setMobileOpen(false);
  }, [active, user?.authorization_revision]);
  useEffect(() => {
    if (!mobileOpen) return;
    const close = (event) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        mobileToggle.current?.focus();
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [mobileOpen]);

  useEffect(() => {
    const close = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const allSelected =
    organizations.length > 0 && organizationIds.length === organizations.length;
  const label = allSelected
    ? allCustomersSelected
      ? "ALL customers"
      : "All listed customers"
    : organizationIds.length === 1
      ? organizations.find((o) => o.id === organizationIds[0])?.name ||
        "1 organization"
      : `${organizationIds.length} organizations`;

  const toggleOrganization = (id) => {
    const next = organizationIds.includes(id)
      ? organizationIds.filter((value) => value !== id)
      : [...organizationIds, id];
    onOrganizationChange(next);
  };

  const toggleAll = () => {
    onOrganizationChange(allSelected ? [] : organizations.map((org) => org.id));
  };

  return (
    <header className="topbar">
      <div className="brand">
        <button
          className="brand-link"
          onClick={() => onChange("Overview")}
          aria-label="Go to Overview"
        >
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M3 12h4l3-7 4 14 3-7h4" />
            </svg>
          </span>
          <span>
            OpsControl
            <span className="brand-caption">MONITORING WORKSPACE</span>
          </span>
        </button>
      </div>
      <div className="workspace-breadcrumb">
        <span>Workspace</span>
        <span aria-hidden="true">/</span>
        <b>{active}</b>
      </div>
      <button
        ref={mobileToggle}
        className="mobile-nav-toggle"
        aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
        aria-expanded={mobileOpen}
        aria-controls="primary-navigation"
        onClick={() => setMobileOpen((value) => !value)}
      >
        {mobileOpen ? "Close" : "Menu"}
      </button>
      <nav
        id="primary-navigation"
        aria-label="Primary navigation"
        className={`${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "mobile-nav-open" : ""}`}
      >
        <button
          className="sidebar-toggle"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((v) => !v)}
        >
          {collapsed ? "→" : "←"}
        </button>
        {sections.map((section) => {
          const visible = section.items.filter(([key, , child]) =>
            child ? canOpenSection(user, key, child) : canNavigate(user, key));
          return visible.length ? (
            <div className="nav-group" key={section.name}>
              <span className="nav-section-label">{section.name}</span>
              {visible.map(([key, label, child]) => (
                <button
                  key={child || key}
                  aria-label={child ? label : key}
                  title={collapsed ? label : undefined}
                  aria-current={active === key && (!child || activeSection === child) ? "page" : undefined}
                  className={active === key && (!child || activeSection === child) ? "nav-button active" : "nav-button"}
                  onClick={() => {
                    onChange(key, child ? { section: child } : {});
                    if (mobileOpen) mobileToggle.current?.focus();
                    setMobileOpen(false);
                  }}
                >
                  <NavIcon name={key} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          ) : null;
        })}
        <div className="sidebar-footnote">
          <span className="sidebar-footnote-mark" aria-hidden="true">
            ◈
          </span>
          <b>
            Your operations.
            <br />
            One clear view.
          </b>
          <small>Health · Evidence · Investigation</small>
        </div>
      </nav>
      {administrationPage(active) ? (
        <div className="global-context" aria-label="Administration context">
          <span className="muted">
            {active === "Access Management"
              ? "Service provider · internal access"
              : "Organization inventory · independent filters"}
          </span>
        </div>
      ) : (
        <div className="global-context" ref={ref}>
          <label className="environment-selector">
            <span className="sr-only">Global environment</span>
            <select
              aria-label="Global environment"
              value={environment}
              onChange={(e) => onEnvironmentChange?.(e.target.value)}
            >
              <option value="">All environments</option>
              {["PROD", "QA", "TEST", "DEV", "SANDBOX"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <span className="context-label">Organization</span>
          <button
            disabled={!organizations.length}
            className={open ? "org-context-button open" : "org-context-button"}
            onClick={() => setOpen((value) => !value)}
            aria-haspopup="true"
            aria-expanded={open}
          >
            <span className="org-context-label">{label}</span>
            <span className="org-context-chevron">▾</span>
          </button>
          {open && (
            <div className="org-menu">
              {allCustomersAuthorized && (
                <label className="org-option">
                  <input
                    type="checkbox"
                    checked={allCustomersSelected}
                    onChange={(e) => onAllCustomersChange(e.target.checked)}
                  />
                  <span>
                    <b>ALL customers</b>
                    <small>
                      Explicit elevated scope; future customers follow your
                      grant
                    </small>
                  </span>
                </label>
              )}
              <label className="org-option org-option-all">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                />
                <span>
                  <b>Select every listed customer</b>
                  <small>
                    Explicit current customer IDs; this does not grant ALL
                  </small>
                </span>
              </label>
              <div className="org-menu-divider" />
              {organizations.map((org) => (
                <label className="org-option" key={org.id}>
                  <input
                    type="checkbox"
                    checked={organizationIds.includes(org.id)}
                    onChange={() => toggleOrganization(org.id)}
                  />
                  <span>
                    <b>{org.name}</b>
                    <small>{org.code}</small>
                  </span>
                </label>
              ))}
              {!organizations.length && (
                <div className="org-empty">No authorized organizations.</div>
              )}
            </div>
          )}
        </div>
      )}
      <InAppNotifications user={user} />
      <ThemeToggle />
    </header>
  );
}
