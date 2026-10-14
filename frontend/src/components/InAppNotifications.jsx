import { useEffect, useState } from "react";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
export default function InAppNotifications({ user }) {
  const [open, setOpen] = useState(false),
    [data, setData] = useState(null),
    [preference, setPreference] = useState(null),
    [error, setError] = useState("");
  const allowed = hasPermission(user, "alerts.view");
  useEffect(() => {
    let live = true;
    setData(null);
    setPreference(null);
    setError("");
    if (open && allowed)
      Promise.all([
        control("/api/v1/notifications"),
        control("/api/v1/notifications/preferences"),
      ])
        .then(([notes, config]) => {
          if (live) {
            setData(notes);
            setPreference(config);
          }
        })
        .catch((e) => {
          if (live) setError(e.message);
        });
    return () => {
      live = false;
    };
  }, [open, allowed, user?.id, user?.authorization_revision]);
  if (!allowed) return null;
  const save = async (in_app) => {
    try {
      setPreference(
        await control("/api/v1/notifications/preferences", "PUT", { in_app }),
      );
      setError("");
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <div className="notifications-control">
      <button
        aria-expanded={open}
        aria-controls="personal-notifications"
        onClick={() => setOpen(!open)}
      >
        Notifications
      </button>
      {open && (
        <section
          id="personal-notifications"
          aria-label="Personal notifications"
          className="panel"
        >
          <h2>Notifications</h2>
          {error && <p role="alert">{error}</p>}
          {preference && (
            <label>
              <input
                type="checkbox"
                checked={preference.in_app}
                onChange={(e) => save(e.target.checked)}
              />
              Receive in-app notifications
            </label>
          )}
          {!data && !error && <p>Loading notifications…</p>}
          {data && (
            <>
              <p>
                {data.total} notifications · latest {data.items.length}
              </p>
              <ul>
                {data.items.map((note) => (
                  <li key={note.id}>
                    <strong>{note.severity}</strong> {note.message}{" "}
                    <time>{new Date(note.created_at).toLocaleString()}</time>
                  </li>
                ))}
              </ul>
              {!data.items.length && (
                <p>No notifications delivered to your account.</p>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
