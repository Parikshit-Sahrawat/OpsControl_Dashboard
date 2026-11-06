import { useEffect, useRef, useState } from "react";
import { control } from "./controlPlane";
import { selectionGuard } from "./workflowConfiguration";

export default function ETLNativeBindings({
  organizationId,
  workflowId,
  jobId,
  allowed,
  onChange,
}) {
  const [versions, setVersions] = useState([]),
    [candidates, setCandidates] = useState([]),
    [candidate, setCandidate] = useState(""),
    [authority, setAuthority] = useState(""),
    [methods, setMethods] = useState([]),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false);
  const guard = useRef(selectionGuard());
  const base = `/api/v1/etl/workflows/${workflowId}/jobs/${jobId}`;
  const request = (path, method, body, signal) =>
    control(base + path, method, body, {
      customerIds: [organizationId],
      signal,
    });
  useEffect(() => {
    const generation = guard.current.next(),
      abort = new AbortController();
    setVersions([]);
    setCandidates([]);
    setCandidate("");
    setAuthority("");
    setMethods([]);
    setReason("");
    setError("");
    setBusy(false);
    setLoaded(false);
    Promise.all([
      control(base + "/native-bindings", "GET", undefined, {
        customerIds: [organizationId],
        signal: abort.signal,
      }),
      control(base + "/native-binding-options", "GET", undefined, {
        customerIds: [organizationId],
        signal: abort.signal,
      }),
    ])
      .then(([history, options]) => {
        if (!guard.current.current(generation)) return;
        setVersions(history.versions);
        setCandidates(options.candidates);
        setLoaded(true);
        const current = history.versions.find((v) => !v.valid_until);
        if (current) {
          setCandidate(current.native_job_id);
          setAuthority(current.identity_snapshot.authority_claim);
          setMethods(current.method_snapshot.map((m) => m.method_id));
        }
      })
      .catch((e) => {
        if (guard.current.current(generation) && e.name !== "AbortError")
          setError(e.message);
      });
    return () => {
      guard.current.next();
      abort.abort();
    };
  }, [base, organizationId]);
  const current = versions.find((v) => !v.valid_until);
  const selected = candidates.find((c) => c.id === candidate);
  async function apply(command) {
    if (!candidate) {
      setError("Native Job candidate is required");
      return;
    }
    if (!/^[A-Za-z0-9._:/@-]{3,200}$/.test(authority)) {
      setError(
        "Native authority claim must be 3–200 identifier characters; do not enter credentials",
      );
      return;
    }
    if (!methods.length) {
      setError("Select at least one collection method");
      return;
    }
    if (reason.trim().length < 3) {
      setError("A configuration reason is required");
      return;
    }
    const ticket = guard.current.next();
    setBusy(true);
    setError("");
    const expected = Object.fromEntries(
      (selected?.methods || [])
        .filter((m) => methods.includes(m.id))
        .map((m) => [m.source_id, m.generation]),
    );
    try {
      await request("/native-bindings", "POST", {
        command,
        idempotency_key: window.crypto.randomUUID(),
        current_binding_id: current?.id || null,
        expected_revision: current?.revision || null,
        native_job_id: candidate,
        authority_claim: authority,
        method_ids: methods,
        expected_sources: expected,
        reason: reason.trim(),
        confirmed: true,
      });
      const data = await request("/native-bindings", "GET");
      if (!guard.current.current(ticket)) return;
      setVersions(data.versions);
      setReason("");
      try {
        await onChange?.();
      } catch {
        if (guard.current.current(ticket))
          setError(
            "Configuration saved; readiness refresh failed. Reload to review current state.",
          );
      }
    } catch (e) {
      if (guard.current.current(ticket)) setError(e.message);
    } finally {
      if (guard.current.current(ticket)) setBusy(false);
    }
  }
  return (
    <section aria-label="Native binding configuration">
      <h5>Native binding</h5>
      <p>
        Identity claims remain unverified until independently qualified. Saving
        never activates monitoring.
      </p>
      {error && <p role="alert">{error}</p>}
      {!loaded && !error && <p role="status">Loading native binding…</p>}
      {loaded && !candidates.length && (
        <p>
          No scoped native candidate exists for this Job. Register an explicit
          candidate in its monitoring integration first.
        </p>
      )}
      {loaded && <p>Current binding: {current?.state || "MISSING"}</p>}
      {allowed && loaded && candidates.length > 0 && (
        <fieldset disabled={busy || current?.state === "RETIRED"}>
          <legend>Monitoring configuration only</legend>
          <div className="form-grid">
            <div>
              <label htmlFor={`native-candidate-${jobId}`}>
                Native Job candidate
              </label>
              <select
                id={`native-candidate-${jobId}`}
                value={candidate}
                disabled={!!current}
                onChange={(e) => {
                  setCandidate(e.target.value);
                  setMethods([]);
                }}
              >
                <option value="">Select native Job</option>
                {candidates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} · {c.native_id}
                  </option>
                ))}
              </select>
            </div>
            <label>
              Native authority claim
              <input
                value={authority}
                disabled={!!current}
                onChange={(e) => setAuthority(e.target.value)}
                autoComplete="off"
              />
            </label>
          </div>
          <p>
            Use the exact provider namespace identifier. A display name alone is
            insufficient. Never enter secrets.
          </p>
          <fieldset>
            <legend>Collection methods</legend>
            {selected?.methods.map((m) => (
              <label key={m.id}>
                <input
                  type="checkbox"
                  checked={methods.includes(m.id)}
                  onChange={() =>
                    setMethods((old) =>
                      old.includes(m.id)
                        ? old.filter((v) => v !== m.id)
                        : [...old, m.id],
                    )
                  }
                />
                {m.name} · {m.validation}
              </label>
            ))}
          </fieldset>
          <label>
            Configuration change reason
            <input
              value={reason}
              maxLength={500}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          {!current ? (
            <button onClick={() => apply("STAGE")}>Stage binding claim</button>
          ) : (
            <>
              <button onClick={() => apply("REPLACE")}>
                Replace reader binding
              </button>
              <button onClick={() => apply("CONFIRM")}>
                Request binding confirmation
              </button>
              <button onClick={() => apply("RETIRE")}>Retire binding</button>
            </>
          )}
        </fieldset>
      )}
      {!allowed && (
        <p>
          Read-only binding history. ETL configuration permission is required
          for changes.
        </p>
      )}
      <ol aria-label="Binding history">
        {versions.map((v) => (
          <li key={v.id}>
            <strong>{v.state}</strong> · Version {v.id} · {v.valid_from} →{" "}
            {v.valid_until || "current"}
            <p>
              Native identity: {v.identity_snapshot.platform} /{" "}
              {v.identity_snapshot.authority_claim} /{" "}
              {v.identity_snapshot.native_id}
            </p>
            <p>
              Reason: {v.reason} · Actor {v.actor_id} · Operation{" "}
              {v.operation_id}
            </p>
            <ul>
              {v.method_snapshot.map((m) => (
                <li key={m.method_id}>
                  Method {m.method_id} · Source {m.source_id} · Generation{" "}
                  {m.generation} · Fence {m.fence}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}
