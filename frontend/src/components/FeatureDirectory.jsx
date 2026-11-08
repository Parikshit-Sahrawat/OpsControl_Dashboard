import { useEffect, useRef, useState, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { visibleFeatureGroups } from '../featureDirectory.js';
import NavIcon from './NavIcon';

export default function FeatureDirectory({user, active, activeSection, collapsed, onNavigate}) {
  const groups = visibleFeatureGroups(user);
  const current = groups.find(group => group.items.some(([page]) => page === active))?.name;
  const [expanded, setExpanded] = useState(() => {
    try { return JSON.parse(localStorage.getItem('opscontrol.navGroups') || '{}'); } catch { return {}; }
  });
  const [flyout, setFlyout] = useState(null), [position, setPosition] = useState({left:224,top:110});
  const panel = useRef(null), trigger = useRef(null);
  const group = groups.find(g => g.name === flyout);
  const close = (restore=false) => { setFlyout(null); if(restore)trigger.current?.focus(); };
  useEffect(() => {localStorage.setItem('opscontrol.navGroups',JSON.stringify(expanded));},[expanded]);
  useEffect(() => {setFlyout(null);},[active,activeSection,user.id,user.authorization_revision,collapsed]);
  useLayoutEffect(() => {
    if(!group)return;
    const place=()=>{const rect=trigger.current?.getBoundingClientRect();if(rect)setPosition({left:Math.max(12,Math.min((trigger.current?.closest("nav")?.getBoundingClientRect().right||rect.right)+8,window.innerWidth-300)),top:Math.max(12,Math.min(rect.top,window.innerHeight-(panel.current?.offsetHeight||320)-12))});};
    place();panel.current?.querySelector('button')?.focus();
    const outside=e=>{if(!panel.current?.contains(e.target)&&!trigger.current?.contains(e.target))setFlyout(null);};
    const key=e=>{if(e.key==='Escape'||e.key==='ArrowLeft'){e.preventDefault();setFlyout(null);trigger.current?.focus();}};
    document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key);
    window.addEventListener('resize',place);window.addEventListener('scroll',place,true);
    return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key);window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);};
  },[flyout,user.authorization_revision]);
  const open=(name,event)=>{trigger.current=event.currentTarget;setFlyout(previous=>previous===name?null:name);};
  const itemButton=([page,label,section])=><button type="button" key={section||page} aria-label={section?label:page} aria-current={active===page&&(!section||activeSection===section)?'page':undefined} className={active===page&&(!section||activeSection===section)?'nav-button active':'nav-button'} onClick={()=>{close();onNavigate(page,section?{section}:{});}}><NavIcon name={page}/><span>{label}</span></button>;
  return <>
    <div className="feature-directory-heading">Feature Directory</div>
    {groups.map(g=>{const isExpanded=expanded[g.name] ?? g.name===current;const id='directory-'+g.name.replaceAll(' ','-').toLowerCase();return <div className="nav-group" role="group" aria-label={g.name} key={g.name}>
      <div className="feature-category-row">
        <button type="button" className="nav-group-toggle" aria-label={`${g.name} navigation`} title={g.name} aria-haspopup={collapsed?"dialog":undefined} aria-expanded={collapsed?flyout===g.name:isExpanded} aria-controls={collapsed?(flyout===g.name?"feature-directory-flyout":undefined):id} onClick={event=>collapsed?open(g.name,event):setExpanded(previous=>({...previous,[g.name]:!isExpanded}))} onKeyDown={event=>{if(event.key==='ArrowRight'){event.preventDefault();open(g.name,event);}}}><NavIcon name={g.items[0][0]}/><span>{g.name}</span><span className="category-chevron" aria-hidden="true">{isExpanded?'⌄':'›'}</span></button>
        {!collapsed&&<button type="button" className="feature-flyout-trigger" aria-haspopup="dialog" aria-label={`Open ${g.name} features`} aria-expanded={flyout===g.name} aria-controls={flyout===g.name?'feature-directory-flyout':undefined} onClick={event=>open(g.name,event)}>›</button>}
      </div>
      <div id={id} className="nav-group-items" hidden={collapsed||!isExpanded}>{g.items.map(itemButton)}</div>
    </div>;})}
    {group&&createPortal(<section id="feature-directory-flyout" ref={panel} role="dialog" aria-label={`${group.name} features`} onBlur={event=>{if(event.relatedTarget&&!event.currentTarget.contains(event.relatedTarget)&&!trigger.current?.contains(event.relatedTarget))close();}} className="feature-directory-flyout" style={position} onKeyDown={event=>{const buttons=[...panel.current.querySelectorAll('button')];const i=buttons.indexOf(document.activeElement);const next=event.key==='ArrowDown'?(i+1)%buttons.length:event.key==='ArrowUp'?(i+buttons.length-1)%buttons.length:event.key==='Home'?0:event.key==='End'?buttons.length-1:null;if(next!==null){event.preventDefault();buttons[next].focus();}}}>
      <div className="feature-flyout-heading"><h2>{group.name}</h2><button type="button" aria-label="Close feature flyout" onClick={()=>close(true)}>×</button></div>
      <p>Authorized destinations</p>{group.items.map(itemButton)}
    </section>,document.body)}
  </>;
}
