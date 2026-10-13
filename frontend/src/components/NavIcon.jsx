const paths = {
  Overview: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  "ETL Monitoring": "M4 5h16M4 12h16M4 19h16M8 3v4m8 3v4m-8 3v4",
  "VM Health": "M4 3h16v7H4zM4 14h16v7H4zM7 6h.01M7 17h.01M11 6h6m-6 11h6",
  "API Monitoring": "m8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18",
  Alerts: "M12 3 2 21h20L12 3Zm0 6v5m0 3h.01",
  Reports: "M4 3v18h17M8 16v-5m5 5V7m5 9V4",
  "Resource Management": "m12 2 9 5v10l-9 5-9-5V7l9-5ZM3 7l9 5 9-5m-9 5v10",
  "Monitoring Setup": "M3 7h18M3 17h18M8 4v6m8 4v6",
  "Access Management": "M12 3 4 6v6c0 4 8 9 8 9s8-5 8-9V6l-8-3Zm-3 9 2 2 4-4",
};
export default function NavIcon({ name }) {
  return (
    <svg
      className="nav-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.Overview} />
    </svg>
  );
}
