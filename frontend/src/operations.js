import { useEffect, useState } from "react";
import { authHeaders } from "./auth";
const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export async function operations(path, options={}) {
  const response = await fetch(BASE+"/api/v1/operations"+path,{...options,headers:{"Content-Type":"application/json",...authHeaders()}});
  if(!response.ok){let message="Operational evidence unavailable";try{message=(await response.json()).detail||message;}catch{}throw new Error(message);}
  return response.json();
}
export function scopeQuery(ids, extra={}) {
  const query=new URLSearchParams();ids.forEach(id=>query.append("organization_id",id));
  Object.entries(extra).forEach(([key,value])=>{if(value!=="ALL"&&value!==""&&value!=null)query.set(key,value);});
  return query.toString();
}
export function useOperationalFeed(path) {
  const [state,setState]=useState({data:null,error:""}),[revision,setRevision]=useState(0);
  useEffect(()=>{
    let live=true, pending=false; const controllers=new Set();setState({data:null,error:""});
    const refresh=async()=>{if(pending)return;pending=true;const controller=new AbortController();controllers.add(controller);
      try{const data=await operations(path,{signal:controller.signal});if(live)setState({data,error:""});}
      catch(error){if(live&&error.name!=="AbortError")setState({data:null,error:error.message});}
      finally{pending=false;controllers.delete(controller);}};
    if(!path)return;
    refresh();const timer=setInterval(refresh,5000);
    return()=>{live=false;clearInterval(timer);controllers.forEach(c=>c.abort());};
  },[path,revision]);
  return {...state,refresh:()=>setRevision(value=>value+1)};
}
export const evidenceTime = value=>value?new Date(value).toLocaleString("en-IN",{timeZone:"Asia/Kolkata",hour12:false})+" IST":"—";
