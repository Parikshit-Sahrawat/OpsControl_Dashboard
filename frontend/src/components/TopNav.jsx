import { useEffect, useRef, useState } from "react";
import { administrationPage } from "../permissions";
import { FEATURE_GROUPS as sections } from "../featureDirectory.js";
import FeatureDirectory from "./FeatureDirectory";
import ThemeToggle from "./ThemeToggle";
import WorldClock from "./WorldClock";
import useDialogFocus from "./useDialogFocus";
import InAppNotifications from "./InAppNotifications";
import PersonalWorkspace from "./PersonalWorkspace";
import GlobalResourceSearch from "./GlobalResourceSearch";
import { configurationCapable } from "../workspaceFilters";

const environmentChoices = ["PROD", "QA", "TEST", "DEV", "SANDBOX"];

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
  const configMode = configurationCapable(user, organizationIds);
  const [density, setDensity] = useState(() => localStorage.getItem("opscontrol.density") === "comfortable" ? "comfortable" : "compact");
  useEffect(() => { document.documentElement.dataset.density = density; localStorage.setItem("opscontrol.density", density); }, [density]);
  const [personal, setPersonal] = useState(null);
  const [open, setOpen] = useState(false);
  const [envOpen, setEnvOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileToggle = useRef(null);
  const navigation = useRef(null);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("opscontrol.sidebarCollapsed") === "true",
  );
  useEffect(() => {
    document.documentElement.dataset.sidebar = collapsed
      ? "collapsed"
      : "expanded";
    localStorage.setItem("opscontrol.sidebarCollapsed", String(collapsed));
  }, [collapsed]);
  useDialogFocus(navigation, mobileOpen, () => setMobileOpen(false));
  const preferencePanel=useRef(null);
  useEffect(()=>{const resize=()=>{if(preferencePanel.current)preferencePanel.current.open=window.innerWidth>=1800;};resize();window.addEventListener("resize",resize);return()=>window.removeEventListener("resize",resize);},[]);
  const ref = useRef(null);
  useEffect(() => {
    setOpen(false);
    setEnvOpen(false);
    setMobileOpen(false);
  }, [active, user?.authorization_revision]);
  useEffect(() => {
    if (!mobileOpen) return;
    navigation.current?.querySelector(".nav-group-toggle, .nav-button")?.focus();
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
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
        setEnvOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    const escape = (event) => {
      if (event.key === "Escape") { setOpen(false); setEnvOpen(false); }
    };
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, []);
  const selectedEnvironments = Array.isArray(environment) ? environment : environment ? [environment] : [];
  const toggleEnvironment = (value) => onEnvironmentChange?.(
    selectedEnvironments.includes(value)
      ? selectedEnvironments.filter((item) => item !== value)
      : [...selectedEnvironments, value],
  );

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

  const currentGroup = sections.find((section) => section.items.some(([key]) => key === active));
  const currentDestination = currentGroup?.items.find(([key, , child]) =>
    key === active && (!child || child === activeSection));
  return (
    <header className="topbar" data-workspace-mode={configMode ? "configuration" : "operations"}>
      <div className="brand">
        <button
          className="brand-link"
          onClick={() => onChange("Overview")}
          aria-label="Go to Dashboard"
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
      <div className="workspace-breadcrumb" aria-label="Current page">
        <span>{currentGroup?.name || "Workspace"}</span>
        <span aria-hidden="true">/</span>
        <b>{currentDestination?.[1] || active}</b>
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
        ref={navigation}
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
          {collapsed ? "+" : "×"}
        </button>
        <FeatureDirectory user={user} active={active} activeSection={activeSection} collapsed={collapsed} onNavigate={(page,target)=>{onChange(page,target);if(mobileOpen)mobileToggle.current?.focus();setMobileOpen(false);}} />
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
          <div className="environment-selector">
            <button type="button" aria-label="Global environments" aria-expanded={envOpen} aria-controls="environment-options"
              onClick={() => { setEnvOpen((value) => !value); setOpen(false); }}>
              <span className="environment-label" title={selectedEnvironments.join(", ") || "All environments"}>{selectedEnvironments.length ? selectedEnvironments.join(", ") : "All environments"}</span><span aria-hidden="true">▾</span>
            </button>
            {envOpen && <fieldset id="environment-options" className="environment-options">
              <legend>Environment filter</legend>
              <button type="button" onClick={() => onEnvironmentChange?.([])}>All environments</button>
              {environmentChoices.map((value) => <label key={value}><input type="checkbox" checked={selectedEnvironments.includes(value)} onChange={() => toggleEnvironment(value)} />{value}</label>)}
            </fieldset>}
          </div>
          <span className="context-label">Organization</span>
          <button
            disabled={!organizations.length}
            className={open ? "org-context-button open" : "org-context-button"}
            onClick={() => { setOpen((value) => !value); setEnvOpen(false); }}
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
      <GlobalResourceSearch key={user.id+user.authorization_revision+organizationIds.join(",")+JSON.stringify(environment)} user={user} organizationIds={organizationIds} environment={environment} onSelect={resource => onChange("Resource Management", { section: "resources", resourceId: resource.id, resourceDomain: resource.domain, resourceOrganizationId: resource.organization_id })} />
      <details ref={preferencePanel} className="utility-preferences"><summary aria-label="Display preferences">Display</summary><div className="utility-preference-panel"><div className="utility-clock"><WorldClock /></div><label className="density-selector"><span>Density</span><select aria-label="Display density" value={density} onChange={e => setDensity(e.target.value)}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label></div></details>
      <div className="workspace-role" aria-label="Workspace permissions">{configMode ? "Configuration access" : "Operations view"}</div>
      <div className="personal-workspace-actions">
      <button className="filter-button" type="button" onClick={() => setPersonal("profile")}>My profile</button>
      <button className="filter-button" type="button" onClick={() => setPersonal("help")}>Help</button>
      </div>
      {personal && <PersonalWorkspace key={`${user?.id}:${user?.authorization_revision}:${personal}`} kind={personal} user={user} onClose={() => setPersonal(null)} />}
      <InAppNotifications user={user} />
      <ThemeToggle />
    </header>
  );
}
