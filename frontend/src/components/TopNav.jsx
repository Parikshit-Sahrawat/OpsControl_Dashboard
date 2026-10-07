const items = ["Overview", "ETL Jobs", "VM Health", "APIs", "Incidents", "Reports", "Resource Management"];

export default function TopNav({ active, onChange }) {
  return (
    <header className="topbar">
      <div className="brand">OpsControl</div>
      <nav>
        {items.map((item) => (
          <button key={item} className={active === item ? "nav-button active" : "nav-button"} onClick={() => onChange(item)}>
            {item}
          </button>
        ))}
      </nav>
    </header>
  );
}