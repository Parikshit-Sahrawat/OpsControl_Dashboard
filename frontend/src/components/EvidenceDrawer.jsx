import { useEffect, useRef } from "react";
export default function EvidenceDrawer({title,onClose,children}) {
  const ref=useRef(null);
  useEffect(()=>{const previous=document.activeElement;ref.current?.querySelector('button')?.focus();return()=>{if(previous?.isConnected)previous.focus();};},[]);
  const keyboard=event=>{if(event.key==="Escape")onClose();if(event.key==="Tab"){
    const targets=[...ref.current.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),textarea:not(:disabled),select:not(:disabled)')].filter(node=>node.getClientRects().length);
    const first=targets[0],last=targets.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  }};
  return <div className="evidence-backdrop" onClick={onClose}><aside ref={ref} role="dialog" aria-modal="true" aria-label={title} className="evidence-drawer" onClick={event=>event.stopPropagation()} onKeyDown={keyboard}>
    <div className="section-heading-row"><h2>{title}</h2><button onClick={onClose} aria-label="Close evidence">Close</button></div>{children}
  </aside></div>;
}
