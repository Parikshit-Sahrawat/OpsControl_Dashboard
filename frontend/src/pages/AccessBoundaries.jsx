import { useState } from "react";
import usePipelineFeed from "../pipelines/usePipelineFeed";
import { State, Table, Identifier, MutationForm } from "../pipelines/ui";
const empty = {
  permissions: [],
  customers: [],
  departments: [],
  environments: [],
  resources: [],
  role_id: null,
  include_future: false,
  create_departments: false,
};
function Choices({ label, values, options, onChange }) {
  return (
    <label className="form-field">
      {label}
      <select
        multiple
        size={Math.min(5, Math.max(2, options.length))}
        value={values}
        onChange={(e) =>
          onChange([...e.target.selectedOptions].map((o) => o.value))
        }
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}
export default function AccessBoundaries({
  user,
  people,
  departments,
  customers,
  roles,
  catalog,
}) {
  const feed = usePipelineFeed("/api/v1/access/boundaries"),
    [selected, setSelected] = useState(null),
    [subject, setSubject] = useState(""),
    [kind, setKind] = useState("LIMIT"),
    [spec, setSpec] = useState(empty),
    [active, setActive] = useState(true),
    [epoch, setEpoch] = useState(0);
  const change = (key, value) => setSpec((s) => ({ ...s, [key]: value }));
  const edit = (row) => {
    setSelected(row);
    setSubject(row.user_id || "");
    setKind(row.kind);
    setSpec({ ...empty, ...row.specification });
    setActive(row.active);
    setEpoch((e) => e + 1);
  };
  return (
    <details className="card" aria-label="Scope and delegated administration">
      <summary>
        Scope restrictions, delegated administration and ALL-customer authority
      </summary>
      <p>
        These explicit boundaries constrain existing assignments. ALL requires
        an assigned role and an explicit future-customer decision. New
        departments and employees receive no operational access automatically.
      </p>
      <State feed={feed} />
      <Table
        label="Access boundaries"
        headers={[
          "Kind / subject",
          "Customer / department scope",
          "Permissions / restrictions",
          "Revision",
          "State",
          "Review",
        ]}
      >
        {feed.data?.items.map((b) => (
          <tr key={b.id}>
            <td>
              {b.kind}
              <small>
                <Identifier value={b.user_id || b.department_id} />
              </small>
            </td>
            <td>
              {b.specification.customers
                .map((id) => customers.find((c) => c.id === id)?.name || id)
                .join(", ") || "No current customer IDs"}
              <small>
                {b.specification.include_future
                  ? "Includes future customers"
                  : "Explicit current scope only"}
              </small>
              <small>
                {b.specification.departments
                  .map((id) => departments.find((d) => d.id === id)?.name || id)
                  .join(", ")}
              </small>
            </td>
            <td>
              {b.specification.permissions.join(", ")}
              <small>
                {b.specification.environments.join(", ")}{" "}
                {b.specification.resources.join(", ")}
              </small>
            </td>
            <td>{b.revision}</td>
            <td>{b.active === false ? "Inactive" : "Active"}</td>
            <td>
              {user.platform_admin && (
                <button onClick={() => edit(b)}>Review / revise</button>
              )}
            </td>
          </tr>
        ))}
      </Table>
      {user.platform_admin ? (
        <>
          <button
            onClick={() => {
              setSelected(null);
              setSubject("");
              setKind("LIMIT");
              setSpec(empty);
              setActive(true);
              setEpoch((e) => e + 1);
            }}
          >
            New explicit boundary
          </button>
          <MutationForm
            key={epoch}
            method={selected ? "PATCH" : "POST"}
            label="Save explicit access boundary"
            path={
              "/api/v1/access/boundaries" + (selected ? "/" + selected.id : "")
            }
            body={(reason, key) => ({
              user_id: subject || null,
              department_id: selected?.department_id || null,
              kind,
              specification: spec,
              active,
              expected_revision: selected?.revision || null,
              idempotency_key: key,
              reason,
            })}
            disabled={
              feed.stale ||
              feed.loading ||
              (!subject && !selected?.department_id)
            }
            onSaved={() => {
              feed.refresh();
              setEpoch((e) => e + 1);
              setSelected(null);
              setSubject("");
              setSpec(empty);
            }}
          >
            <label>
              Employee
              <select
                required={!selected?.department_id}
                disabled={Boolean(selected)}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              >
                <option value="">Select employee</option>
                {people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name} · {p.username}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Boundary kind
              <select
                disabled={Boolean(selected)}
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value);
                  setSpec(empty);
                }}
              >
                {["LIMIT", "DENY", "DELEGATE", "ALL_CUSTOMERS"].map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            </label>
            <Choices
              label="Implemented permission budget"
              values={spec.permissions}
              options={catalog.map((p) => ({ id: p.key, name: p.key }))}
              onChange={(v) => change("permissions", v)}
            />
            <Choices
              label="Explicit customer IDs"
              values={spec.customers}
              options={customers}
              onChange={(v) => change("customers", v)}
            />
            {kind === "DELEGATE" && (
              <>
                <Choices
                  label="Managed internal departments"
                  values={spec.departments}
                  options={departments}
                  onChange={(v) => change("departments", v)}
                />
                <label>
                  <input
                    type="checkbox"
                    checked={spec.create_departments}
                    onChange={(e) =>
                      change("create_departments", e.target.checked)
                    }
                  />
                  May create empty departments within this existing budget
                </label>
              </>
            )}
            {["LIMIT", "DENY"].includes(kind) && (
              <>
                <Choices
                  label="Environments"
                  values={spec.environments}
                  options={["PROD", "QA", "TEST", "DEV", "SANDBOX"].map(
                    (id) => ({ id, name: id }),
                  )}
                  onChange={(v) => change("environments", v)}
                />
                <label>
                  Resource IDs (comma-separated UUIDs)
                  <input
                    value={spec.resources.join(",")}
                    onChange={(e) =>
                      change(
                        "resources",
                        e.target.value
                          .split(",")
                          .map((v) => v.trim())
                          .filter(Boolean),
                      )
                    }
                  />
                </label>
                <p>
                  LIMIT needs an environment or resource. DENY overrides
                  applicable allows. Unknown or ambiguous bindings fail closed.
                </p>
              </>
            )}
            {kind === "ALL_CUSTOMERS" && (
              <>
                <label>
                  Existing assigned role
                  <select
                    required
                    value={spec.role_id || ""}
                    onChange={(e) => change("role_id", e.target.value)}
                  >
                    <option value="">Select assigned role</option>
                    {roles
                      .filter((r) => r.code !== "platform-administrator")
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={spec.include_future}
                    onChange={(e) => change("include_future", e.target.checked)}
                  />
                  Include future customers explicitly (otherwise selected
                  snapshot only)
                </label>
              </>
            )}
            <label>
              <input
                type="checkbox"
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
              />
              Boundary active
            </label>
            <p>
              Revision {selected?.revision || "new"} · consequential
              platform-only decision; reason and confirmation required.
            </p>
          </MutationForm>
        </>
      ) : (
        <p>
          Boundary changes and ALL grants require protected platform authority.
          Your existing delegation budget is read-only here.
        </p>
      )}
    </details>
  );
}
