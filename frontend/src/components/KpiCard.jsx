export default function KpiCard({ label, value, tone = "", detail }) {
  return (
    <article className="card kpi-card">
      <div className="muted">{label}</div>
      <div className={`kpi-value ${tone}`}>{value}</div>
      <div className="muted small">{detail}</div>
    </article>
  );
}