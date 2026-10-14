import { useEffect, useState } from "react";

export const CLOCK_ZONES = [
  ["Asia/Kolkata", "India (IST)"],
  ["UTC", "UTC"],
  ["America/New_York", "New York (ET)"],
  ["America/Chicago", "Chicago (CT)"],
  ["America/Los_Angeles", "Los Angeles (PT)"],
  ["Europe/London", "London (UK)"],
  ["Europe/Berlin", "Berlin (Central Europe)"],
  ["Asia/Dubai", "Dubai (GST)"],
  ["Asia/Singapore", "Singapore (SGT)"],
  ["Asia/Tokyo", "Tokyo (JST)"],
  ["Australia/Sydney", "Sydney (Australia)"],
];

const STORAGE_KEY = "opscontrol.clock.timeZone";
const isSupportedZone = zone => CLOCK_ZONES.some(([name]) => name === zone);

function initialZone() {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (isSupportedZone(saved)) return saved;
  } catch { /* storage can be blocked */ }
  return "Asia/Kolkata";
}

export function formatClock(instant, zone) {
  const time = new Intl.DateTimeFormat("en-GB", {
    timeZone: zone, hour: "2-digit", minute: "2-digit", second: "2-digit",
    hourCycle: "h23",
  }).format(instant);
  const date = new Intl.DateTimeFormat("en-GB", {
    timeZone: zone, weekday: "short", day: "2-digit", month: "short",
    year: "numeric", timeZoneName: "short",
  }).format(instant);
  return { time, date };
}

export default function WorldClock() {
  const [zone, setZone] = useState(initialZone);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  function changeZone(next) {
    if (!isSupportedZone(next)) return;
    setZone(next);
    try { window.localStorage.setItem(STORAGE_KEY, next); } catch { /* optional preference */ }
  }

  const { time, date } = formatClock(now, zone);
  return (
    <div className="world-clock" aria-label="Current world clock">
      <span className="world-clock-symbol" aria-hidden="true">◷</span>
      <div className="world-clock-readout">
        <time dateTime={now.toISOString()} className="world-clock-time">{time}</time>
        <span className="world-clock-date">{date}</span>
      </div>
      <label className="world-clock-zone">
        <span className="sr-only">World clock timezone</span>
        <select aria-label="World clock timezone" value={zone} onChange={event => changeZone(event.target.value)}>
          {CLOCK_ZONES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </label>
    </div>
  );
}
