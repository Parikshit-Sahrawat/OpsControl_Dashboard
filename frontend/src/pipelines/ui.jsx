import { useEffect, useRef, useState } from "react";
import useDialogFocus from "../components/useDialogFocus";
import StatusBadge from "../components/StatusBadge";
import { control } from "../controlPlane";
import { EXPLANATIONS, errorMessage, time } from "./contracts";
export function State({ feed, empty = false }) {
  return (
    <>
      {feed.error && (
        <p role="alert" className="error-banner">
          {errorMessage(feed.error)}{" "}
          {feed.data
            ? "Last received data is stale. Mutations are disabled."
            : ""}
          <button onClick={feed.refresh}>Retry / refresh</button>
        </p>
      )}
      {feed.loading && !feed.data && (
        <p role="status">Loading monitoring evidence…</p>
      )}
      {feed.stale && !feed.error && (
        <p role="status">Stale data · refresh before taking action.</p>
      )}
      {feed.data && empty && (
        <p className="pipeline-empty">
          No matching records in this authorized scope.
        </p>
      )}
    </>
  );
}
export function Status({ value }) {
  return (
    <span title={EXPLANATIONS[value] || value || EXPLANATIONS.UNKNOWN}>
      <StatusBadge status={value || "UNKNOWN"} />
      {EXPLANATIONS[value] && (
        <span className="sr-only"> {EXPLANATIONS[value]}</span>
      )}
    </span>
  );
}
export function Stamp({ value }) {
  return <time dateTime={value || undefined}>{time(value)}</time>;
}
export function Identifier({ value }) {
  return value ? (
    <span className="pipeline-id" title={value}>
      {value}
    </span>
  ) : (
    <span className="muted">Not reported</span>
  );
}
export function Facts({ items }) {
  return (
    <dl className="pipeline-facts">
      {Object.entries(items).map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v ?? "Not reported"}</dd>
        </div>
      ))}
    </dl>
  );
}
export function Pager({
  total = 0,
  offset,
  limit = 20,
  onChange,
  label = "Records",
}) {
  return (
    <nav className="pipeline-pager" aria-label={label + " pagination"}>
      <span>
        {total ? offset + 1 : 0}–{Math.min(offset + limit, total)} of {total}
      </span>
      <button
        disabled={!offset}
        onClick={() => onChange(Math.max(0, offset - limit))}
      >
        Previous page
      </button>
      <button
        disabled={offset + limit >= total}
        onClick={() => onChange(offset + limit)}
      >
        Next page
      </button>
    </nav>
  );
}
export function Table({ headers, children, label }) {
  return (
    <div
      className="pipeline-table"
      role="region"
      aria-label={label}
      tabIndex="0"
    >
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th scope="col" key={h}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
export function Drawer({ title, onClose, children }) {
  const ref = useRef(null);
  useDialogFocus(ref, true, onClose);
  return (
    <div className="pipeline-backdrop">
      <section
        className="pipeline-drawer"
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button onClick={onClose} aria-label="Close detail drawer">
            Close
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
export function Evidence({ value }) {
  if (value == null) return <span className="muted">Not reported</span>;
  if (Array.isArray(value))
    return value.length ? (
      <ul className="pipeline-evidence-list">
        {value.map((v, i) => (
          <li key={i}>
            <Evidence value={v} />
          </li>
        ))}
      </ul>
    ) : (
      <span className="muted">None recorded</span>
    );
  if (typeof value === "object")
    return (
      <dl className="pipeline-evidence">
        {Object.entries(value).map(([k, v]) => (
          <div key={k}>
            <dt>{k.replaceAll("_", " ")}</dt>
            <dd>
              <Evidence value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return (
    <span>
      {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
    </span>
  );
}
export function MutationForm({
  label,
  path,
  body,
  children,
  onSaved,
  disabled = false,
  reasonRequired = true,
  method = "POST",
}) {
  const [reason, setReason] = useState(""),
    [confirmed, setConfirmed] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(null),
    [blocked, setBlocked] = useState(false);
  const alive = useRef(true),
    key = useRef(window.crypto.randomUUID());
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const submit = async (e) => {
    e.preventDefault();
    if (busy || disabled || blocked || !confirmed) return;
    setBusy(true);
    setError(null);
    try {
      await control(
        path,
        method,
        typeof body === "function" ? body(reason, key.current) : body,
      );
      if (alive.current) {
        setReason("");
        setConfirmed(false);
        key.current = window.crypto.randomUUID();
        onSaved?.();
      }
    } catch (e) {
      if (alive.current) {
        setError(e);
        if ([409, 403, 401].includes(e.status)) setBlocked(true);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  };
  return (
    <form className="pipeline-action" onSubmit={submit} aria-label={label}>
      <h3>{label}</h3>
      {children}
      {reasonRequired && (
        <label>
          Decision reason
          <textarea
            required
            minLength={10}
            maxLength={2000}
            disabled={busy}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
      )}
      <label className="pipeline-confirm">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={busy}
          onChange={(e) => setConfirmed(e.target.checked)}
          required
        />
        I reviewed the evidence and confirm {label.toLowerCase()}.
      </label>
      {error && <p role="alert">{errorMessage(error)}</p>}
      {blocked && (
        <button type="button" onClick={onSaved}>
          Refresh record before another decision
        </button>
      )}
      <button
        type="submit"
        disabled={disabled || blocked || busy || !confirmed}
      >
        {busy ? "Saving…" : label}
      </button>
    </form>
  );
}
