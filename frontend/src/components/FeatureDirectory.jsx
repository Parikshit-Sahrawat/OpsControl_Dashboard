import { useEffect, useRef, useState } from 'react';
import { visibleFeatureGroups } from '../featureDirectory.js';
import NavIcon from './NavIcon';

// Only presentation groups are added: every leaf retains its original route,
// permission and selected-customer contract. No off-panel menu or new page.
export default function FeatureDirectory({ user, active, activeSection, collapsed, onExpand, onNavigate }) {
  const groups = visibleFeatureGroups(user);
  const current = groups.find(group => group.items.some(([page]) => page === active))?.name;
  const panel = useRef(null);
  const [expanded, setExpanded] = useState(() => {
    try {
      const value = JSON.parse(localStorage.getItem('opscontrol.navGroups') || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch { return {}; }
  });
  useEffect(() => { try { localStorage.setItem('opscontrol.navGroups', JSON.stringify(expanded)); } catch { /* Navigation works when browser storage is unavailable. */ } }, [expanded]);
  const toggle = (key, value) => setExpanded(previous => ({ ...previous, [key]: value }));
  const keyDown = event => {
    const buttons = [...panel.current.querySelectorAll('button')].filter(button => button.getClientRects().length);
    const index = buttons.indexOf(event.target);
    const next = event.key === 'ArrowDown' ? (index + 1) % buttons.length : event.key === 'ArrowUp' ? (index + buttons.length - 1) % buttons.length : event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : null;
    if (next !== null) { event.preventDefault(); buttons[next]?.focus(); }
    if (event.key === 'ArrowRight' && event.target.getAttribute('aria-expanded') === 'false') { event.preventDefault(); event.target.click(); }
    if (event.key === 'ArrowLeft' || event.key === 'Escape') {
      const parent = event.target.closest('.nav-subgroup') || event.target.closest('.nav-group');
      const trigger = parent?.querySelector('button[aria-expanded]');
      if (trigger?.getAttribute('aria-expanded') === 'true') { event.preventDefault(); trigger.click(); trigger.focus(); }
    }
  };
  const itemButton = ([page, label, section]) => <button type="button" key={section || page} aria-label={section ? label : page} aria-current={active === page && (!section || activeSection === section) ? 'page' : undefined} className={active === page && (!section || activeSection === section) ? 'nav-button active' : 'nav-button'} onClick={() => onNavigate(page, section ? { section } : {})}><NavIcon name={page} /><span>{label}</span></button>;
  return <div ref={panel} onKeyDown={keyDown}>
    <div className="feature-directory-heading">Feature Directory</div>
    {groups.map(group => {
      const open = !collapsed && (expanded[group.name] ?? group.name === current);
      const id = 'directory-' + group.name.replaceAll(' ', '-').toLowerCase();
      const nested = group.name !== "Resource Management" && group.items.every(item => item[2]);
      const subgroup = group.name + ':workspace';
      const subOpen = expanded[subgroup] ?? group.name === current;
      return <div className="nav-group" role="group" aria-label={group.name} key={group.name}>
        <div className="feature-category-row"><button type="button" className="nav-group-toggle" aria-label={`${group.name} navigation`} title={group.name} aria-expanded={open} aria-controls={id} onClick={() => { if (collapsed) onExpand(); toggle(group.name, !open); }}><NavIcon name={group.items[0][0]} /><span>{group.name}</span><span className="category-chevron" aria-hidden="true">{open ? '⌄' : '›'}</span></button></div>
        <div id={id} className="nav-group-items" hidden={!open}>
          {nested ? <div className="nav-subgroup"><button type="button" className="nav-group-toggle" aria-label={`${group.name} workspace navigation`} aria-expanded={subOpen} aria-controls={id + '-workspace'} onClick={() => toggle(subgroup, !subOpen)}><span>Workspace configuration</span><span aria-hidden="true">{subOpen ? '⌄' : '›'}</span></button><div id={id + '-workspace'} hidden={!subOpen} className="nav-nested-items">{group.items.map(itemButton)}</div></div> : group.items.map(itemButton)}
        </div>
      </div>;
    })}
  </div>;
}
