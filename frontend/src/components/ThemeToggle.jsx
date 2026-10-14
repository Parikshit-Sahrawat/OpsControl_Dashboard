import { useSyncExternalStore } from "react";
import { getTheme, setTheme, subscribeTheme } from "../theme";

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, getTheme);
  return <div className="theme-toggle" role="group" aria-label="Appearance">
    <button type="button" aria-label="Light theme" title="Light theme" aria-pressed={theme === "light"} onClick={() => setTheme("light")}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>
    </button>
    <button type="button" aria-label="Dark theme" title="Dark theme" aria-pressed={theme === "dark"} onClick={() => setTheme("dark")}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15.2A8.5 8.5 0 0 1 8.8 4a8.5 8.5 0 1 0 11.2 11.2Z"/></svg>
    </button>
  </div>;
}
