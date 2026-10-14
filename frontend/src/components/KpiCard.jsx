export default function KpiCard({ label, value, tone = "", detail, icon, featured = false }) {
  return (
    <article className={`card kpi-card${featured ? " kpi-card-featured" : ""}`}>
      <div className="kpi-card-head">
        <span className="kpi-label">{label}</span>
        {icon && <span className="kpi-icon" aria-hidden="true">{icon}</span>}
      </div>
      <div className={`kpi-value ${tone}`}>{value}</div>
      <div className="muted small kpi-detail">{detail}</div>
      {icon && <div className="kpi-card-footer" aria-hidden="true">
        <span>View details</span>
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
      </div>}
    </article>
  );
}
