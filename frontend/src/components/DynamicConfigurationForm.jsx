import { useEffect, useState } from "react";
import { control } from "../controlPlane";

// Registry definitions are UI hints. The server remains the validation authority.
export default function DynamicConfigurationForm({
  definition,
  value,
  onChange,
  keys,
  disabled = false,
  context = {},
}) {
  const [registry, setRegistry] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    control("/api/v1/attribute-registry")
      .then((v) => live && setRegistry(v))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, []);
  if (error)
    return <p role="alert">Attribute definitions unavailable: {error}</p>;
  if (!registry) return <p role="status">Loading attribute definitions…</p>;
  const fields = registry.definitions?.[definition]?.fields;
  if (!fields)
    return (
      <p role="alert">
        Configuration definitions unavailable for {definition}.
      </p>
    );
  return (
    <div className="form-grid" data-registry-version={registry.version}>
      {fields
        .filter((f) => !keys || keys.includes(f.key))
        .map((f) => {
          const input = f.input_type?.toUpperCase(),
            type = f.data_type?.toUpperCase();
          const effective = (key) =>
            value[key] ?? fields.find((field) => field.key === key)?.default;
          if (
            f.visible_if &&
            !Object.entries(f.visible_if).every(([key, values]) =>
              values.includes(effective(key)),
            )
          )
            return null;
          const required =
            f.required ||
            (f.required_when &&
              Object.entries(f.required_when).every(([key, values]) =>
                values.includes(effective(key)),
              ));
          const current = value[f.key] ?? f.default ?? "";
          const set = (v) => onChange({ ...value, [f.key]: v });
          const choices = f.allowed_values || [];
          return (
            <label key={f.key} className="field">
              <span>
                {f.label}
                {required ? " *" : ""}
              </span>
              {choices.length ? (
                <select
                  aria-label={f.label}
                  disabled={disabled}
                  value={current}
                  required={Boolean(required)}
                  onChange={(e) => set(e.target.value)}
                >
                  {!required && <option value="">Not configured</option>}
                  {choices.map((v) => (
                    <option
                      key={String(v)}
                      value={v}
                      disabled={Boolean(
                        context.os_type &&
                          f.value_capabilities?.[v]?.os &&
                          !f.value_capabilities[v].os.includes(context.os_type),
                      )}
                    >
                      {String(v)}
                    </option>
                  ))}
                </select>
              ) : type === "BOOLEAN" || input === "CHECKBOX" ? (
                <input
                  aria-label={f.label}
                  disabled={disabled}
                  type="checkbox"
                  checked={Boolean(current)}
                  onChange={(e) => set(e.target.checked)}
                />
              ) : ["OBJECT", "ARRAY", "JSON"].includes(type) ||
                input === "JSON" ? (
                <StructuredInput
                  value={current}
                  label={f.label}
                  disabled={disabled}
                  onChange={set}
                  array={type === "ARRAY"}
                />
              ) : (
                <input
                  aria-label={f.label}
                  disabled={disabled}
                  type={
                    type === "INTEGER" || type === "NUMBER" ? "number" : "text"
                  }
                  value={
                    typeof current === "object"
                      ? JSON.stringify(current)
                      : current
                  }
                  required={Boolean(required)}
                  min={f.validation?.minimum}
                  max={f.validation?.maximum}
                  onChange={(e) =>
                    set(
                      type === "INTEGER" || type === "NUMBER"
                        ? Number(e.target.value)
                        : e.target.value,
                    )
                  }
                  autoComplete="off"
                />
              )}
              {f.description && <small>{f.description}</small>}
              {f.secret_handling && f.secret_handling !== "NONE" && (
                <small>Use a secret reference; never enter a credential.</small>
              )}
            </label>
          );
        })}
    </div>
  );
}

function StructuredInput({ value, onChange, disabled, array, label }) {
  const [text, setText] = useState(() =>
      JSON.stringify(value || (array ? [] : {}), null, 2),
    ),
    [error, setError] = useState("");
  useEffect(
    () => setText(JSON.stringify(value || (array ? [] : {}), null, 2)),
    [JSON.stringify(value)],
  );
  return (
    <>
      <textarea
        aria-label={label}
        disabled={disabled}
        value={text}
        aria-invalid={Boolean(error)}
        onChange={(e) => {
          setText(e.target.value);
          try {
            const parsed = JSON.parse(e.target.value);
            if (
              array
                ? !Array.isArray(parsed)
                : typeof parsed !== "object" ||
                  parsed === null ||
                  Array.isArray(parsed)
            )
              throw Error(array ? "Expected an array" : "Expected an object");
            setError("");
            e.target.setCustomValidity("");
            onChange(parsed);
          } catch (e) {
            setError(e.message);
            e.target.setCustomValidity(
              "Correct the structured attribute before saving",
            );
          }
        }}
      />
      {error && (
        <small role="alert">Invalid structured attribute: {error}</small>
      )}
    </>
  );
}
