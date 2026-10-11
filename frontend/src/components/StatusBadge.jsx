export default function StatusBadge({ status }) {
  const label = typeof status === "string" && status.trim() ? status : "UNKNOWN";
  return <span className={`status status--${label.toLowerCase()}`}><span className="status-indicator" aria-hidden="true" />{label.replaceAll("_", " ")}</span>;
}
