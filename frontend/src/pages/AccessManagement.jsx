import {
  cloneElement,
  useId,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { authHeaders } from "../auth";
import { hasPermission } from "../permissions";
import useDialogFocus from "../components/useDialogFocus";
import "../access-management.css";
import AccessOnboarding from "./AccessOnboarding";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TABS = [
  "Employees",
  "Departments",
  "Roles & Permissions",
  "Access Audit",
];
const PAGE = 25;
async function api(path, method = "GET", payload) {
  const response = await fetch(`${BASE}/api/v1/access${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    ...(payload !== undefined && { body: JSON.stringify(payload) }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `Request rejected (${response.status}). Check the required fields and your permissions.`,
    );
  }
  return response.status === 204 ? null : response.json();
}
// Enumerate administrative option directories in bounded pages. Never silently
// omit employees/departments after the API's first page.
async function directory(path) {
  const rows = [];
  for (let offset = 0; ; offset += 200) {
    const result = await api(`${path}?limit=200&offset=${offset}`);
    rows.push(...result.items);
    if (offset + result.items.length >= result.total || !result.items.length)
      return rows;
  }
}
const params = (values) =>
  new URLSearchParams(
    Object.entries(values).filter(([, v]) => v !== "" && v != null),
  ).toString();
function Field({ label, children }) {
  const id = useId();
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children, { id })}
    </div>
  );
}
const Status = ({ active }) => (
  <span className={`status status--${active ? "success" : "unknown"}`}>
    {active ? "ACTIVE" : "INACTIVE"}
  </span>
);
function Dialog({ title, onClose, children }) {
  const ref = useRef(null);
  useDialogFocus(ref, true, onClose);
  return (
    <div className="modal-backdrop">
      <section
        ref={ref}
        className="modal access-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="modal-header">
          <h2>{title}</h2>
          <button
            className="close-button"
            onClick={onClose}
            aria-label="Close access dialog"
          >
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
function Effective({ value, customers }) {
  if (!value) return <p className="muted">Loading effective permissions…</p>;
  return (
    <div className="access-effective">
      {value.break_glass && (
        <p className="info-box">
          Protected platform administration bypasses customer scopes.
          Configurable roles cannot grant this capability.
        </p>
      )}
      {value.disabled && (
        <p className="info-box">
          Account disabled. No usable session or effective access.
        </p>
      )}
      <h3>Effective permissions</h3>
      <div className="chip-row">
        {value.permissions?.map((k) => (
          <code className="mini-chip" key={k}>
            {k}
          </code>
        ))}
        {!value.permissions?.length &&
          "Default deny — no permissions assigned."}
      </div>
      <h3>Organization scopes</h3>
      {Object.entries(value.customer_permissions || {}).map(([id, keys]) => (
        <div className="access-scope" key={id}>
          <b>{customers.find((c) => c.id === id)?.name || id}</b>
          <div className="chip-row">
            {keys.map((k) => (
              <code className="mini-chip" key={k}>
                {k}
              </code>
            ))}
          </div>
        </div>
      ))}
      <h3>Inherited and directly assigned sources</h3>
      {(value.inherited_and_direct || []).map((source, i) => (
        <p key={i}>
          <span className="mini-chip">{source.source}</span> {source.role} ·{" "}
          {source.scope === "provider"
            ? source.customer_scope_required && !source.permissions?.length
              ? "Organization grant required; no operational access granted"
              : "Service-provider administration"
            : customers.find((c) => c.id === source.customer_id)?.name ||
              source.customer_id}
          <small className="access-uuid">{source.subject_id}</small>
        </p>
      ))}
      {!!value.denied_customers?.length && (
        <p>
          Explicit customer restrictions:{" "}
          {value.denied_customers
            .map((id) => customers.find((c) => c.id === id)?.name || id)
            .join(", ")}
        </p>
      )}
      {!!value.denied_permissions?.length && (
        <p>
          Employee permission restrictions:{" "}
          {value.denied_permissions.join(", ")}
        </p>
      )}
      <p className="muted small">
        Default deny. Customer denies and employee role restrictions narrow
        inherited access. All changes are enforced by the API on the next
        request.
      </p>
    </div>
  );
}

export default function AccessManagement({ user }) {
  const can = (key) => hasPermission(user, `access.${key}`);
  const [tab, setTab] = useState("Departments"),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [department, setDepartment] = useState(""),
    [roleFilter, setRoleFilter] = useState("");
  const [offset, setOffset] = useState(0),
    [data, setData] = useState({ items: [], total: 0 }),
    [roles, setRoles] = useState([]),
    [catalog, setCatalog] = useState([]),
    [customers, setCustomers] = useState([]),
    [departments, setDepartments] = useState([]),
    [people, setPeople] = useState([]),
    [provider, setProvider] = useState(null);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [dialog, setDialog] = useState(null),
    [selected, setSelected] = useState(null),
    [effective, setEffective] = useState(null),
    [members, setMembers] = useState([]),
    [draft, setDraft] = useState({}),
    [detailLoading, setDetailLoading] = useState(false),
    [detailError, setDetailError] = useState("");
  const [onboarding, setOnboarding] = useState(false);
  const epoch = useRef(0),
    detailEpoch = useRef(0);
  const reload = useCallback(async () => {
    const current = ++epoch.current;
    setLoading(true);
    setError("");
    try {
      const path =
        tab === "Employees"
          ? `/employees?${params({ search, active: status, department_id: department, role_id: roleFilter, limit: PAGE, offset })}`
          : tab === "Departments"
            ? `/departments?${params({ search, active: status, limit: PAGE, offset })}`
            : tab === "Access Audit"
              ? `/audit?limit=${PAGE}&offset=${offset}`
              : "/roles";
      const result = await api(path);
      if (current === epoch.current)
        setData(
          Array.isArray(result)
            ? {
                items: result.filter(
                  (r) =>
                    !search ||
                    r.name.toLowerCase().includes(search.toLowerCase()),
                ),
                total: result.length,
              }
            : result,
        );
    } catch (e) {
      if (current === epoch.current) {
        setData({ items: [], total: 0 });
        setError(e.message);
      }
    } finally {
      if (current === epoch.current) setLoading(false);
    }
  }, [tab, search, status, department, roleFilter, offset]);
  const latestReload = useRef(reload);
  latestReload.current = reload;
  const directories = useCallback(async () => {
    const [r, p, c, d, u, org] = await Promise.all([
      api("/roles"),
      api("/permissions"),
      api("/customer-directory"),
      directory("/departments"),
      directory("/employees"),
      api("/provider"),
    ]);
    setRoles(r);
    setCatalog(p);
    setCustomers(c);
    setDepartments(d);
    setPeople(u);
    setProvider(org);
  }, []);
  useEffect(() => {
    let live = true;
    if (can("view")) directories().catch((e) => live && setError(e.message));
    return () => {
      live = false;
      epoch.current++;
    };
  }, [directories, user?.authorization_revision]);
  useEffect(() => {
    if (can("view")) reload();
    return () => {
      epoch.current++;
    };
  }, [reload, user?.authorization_revision]);
  if (!can("view"))
    return (
      <section className="card state-panel" role="alert">
        <h1>Access restricted</h1>
        <p>Access Management requires access.view.</p>
      </section>
    );
  const roleName = (id) => roles.find((r) => r.id === id)?.name || id;
  const customerName = (id) => customers.find((c) => c.id === id)?.name || id;
  const employeeName = (id) => people.find((p) => p.id === id)?.full_name || id;
  const departmentName = (id) =>
    departments.find((d) => d.id === id)?.name || id;
  async function inspectEmployee(row) {
    const version = ++detailEpoch.current;
    setSelected({ ...row, kind: "employee" });
    setEffective(null);
    setDetailLoading(true);
    setDetailError("");
    setError("");
    try {
      const result = await api(`/employees/${row.id}/effective-permissions`);
      if (version === detailEpoch.current) setEffective(result);
    } catch (e) {
      if (version === detailEpoch.current) setDetailError(e.message);
    } finally {
      if (version === detailEpoch.current) setDetailLoading(false);
    }
  }
  async function inspectDepartment(row) {
    const version = ++detailEpoch.current;
    setSelected({ ...row, kind: "department" });
    setMembers([]);
    setDetailLoading(true);
    setDetailError("");
    setError("");
    try {
      const result = await api(`/departments/${row.id}/members`);
      if (version === detailEpoch.current) setMembers(result);
    } catch (e) {
      if (version === detailEpoch.current) setDetailError(e.message);
    } finally {
      if (version === detailEpoch.current) setDetailLoading(false);
    }
  }
  async function act(
    path,
    method,
    body,
    message = "Change saved. Authorization takes effect on the next request.",
  ) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api(path, method, body);
      // Keep the modal busy until the saved snapshot is fully available.
      // Closing earlier lets a new detail selection get erased by this refresh.
      await directories();
      await latestReload.current();
      detailEpoch.current++;
      setSelected(null);
      setNotice(message);
      setDialog(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function open(kind, row = {}) {
    setError("");
    setDialog({ kind, row });
    if (kind === "employee")
      setDraft({
        username: row.username || "",
        department_id: row.department_id || "",
        full_name: row.full_name || "",
        employee_id: row.employee_id || "",
        work_email: row.work_email || "",
        password: "",
        platform_admin: row.platform_admin || false,
      });
    if (kind === "department")
      setDraft({
        name: row.name || "",
        code: row.code || "",
        description: row.description || "",
        manager_id: row.manager_id || "",
        active: row.active ?? true,
      });
    if (kind === "role")
      setDraft({
        name: row.name || "",
        description: row.description || "",
        permissions: row.permissions || [],
        active: row.active ?? true,
      });
    if (kind === "assignment") setDraft({ role_id: "", effect: "ALLOW" });
    if (kind === "member") setDraft({ user_id: "" });
    if (kind === "employee-department") setDraft({ department_id: "" });
    if (kind === "password") setDraft({ new_password: "" });
  }
  function change(key, value) {
    setDraft((d) => ({ ...d, [key]: value }));
  }
  async function save(event) {
    event.preventDefault();
    const { kind, row } = dialog;
    if (kind === "employee") {
      const { password, username, department_id, ...edit } = draft;
      const payload = {
        ...edit,
        employee_id: edit.employee_id || null,
        work_email: edit.work_email || null,
      };
      if (!user.platform_admin) delete payload.platform_admin;
      return act(
        row.id ? `/employees/${row.id}` : "/employees",
        row.id ? "PATCH" : "POST",
        row.id ? payload : { ...payload, username, password, department_id },
      );
    }
    if (kind === "department")
      return act(
        row.id ? `/departments/${row.id}` : "/departments",
        row.id ? "PATCH" : "POST",
        {
          ...draft,
          code: draft.code || null,
          description: draft.description || null,
          manager_id: draft.manager_id || null,
        },
      );
    if (kind === "role")
      return act(
        row.id ? `/roles/${row.id}` : "/roles",
        row.id ? "PATCH" : "POST",
        draft,
      );
    if (
      kind === "password" &&
      !window.confirm(
        "Reset this employee’s password and revoke all existing sessions?",
      )
    )
      return;
    if (kind === "password")
      return act(
        `/employees/${row.id}/password`,
        "POST",
        draft,
        "Password reset. All employee sessions revoked.",
      );
    if (
      ["employee-department", "member"].includes(kind) &&
      !window.confirm(
        "Transfer this employee to the selected department? Existing inherited permissions will be replaced.",
      )
    )
      return;
    if (kind === "employee-department")
      return act(`/employees/${row.id}/department`, "PUT", {
        department_id: draft.department_id,
      });
    if (kind === "member")
      return act(`/employees/${draft.user_id}/department`, "PUT", {
        department_id: row.id,
      });
    if (
      kind === "assignment" &&
      !window.confirm(
        "Apply the displayed role permissions to this identity? Customer access remains limited by existing grants.",
      )
    )
      return;
    if (kind === "assignment")
      return act(
        `/${row.kind === "employee" ? "employees" : "departments"}/${row.id}/roles`,
        "POST",
        draft,
      );
  }
  function confirmAction(message, path, method, body) {
    if (window.confirm(message)) act(path, method, body);
  }
  const protectedTarget = (row) =>
    !user.platform_admin && row.protected_administration && row.id !== user.id;
  const protectedDepartment = (row) =>
    !user.platform_admin &&
    row.roles.some((a) =>
      roles
        .find((r) => r.id === a.id)
        ?.permissions.some(
          (key) => key.startsWith("access.") || key === "audit.view",
        ),
    );
  const actions = (row, kind) => (
    <div className="access-actions">
      <button
        className="filter-button"
        disabled={busy}
        onClick={() =>
          kind === "employee" ? inspectEmployee(row) : inspectDepartment(row)
        }
      >
        {kind === "employee" ? "Review access" : "Members & access"}
      </button>
      {can(kind === "employee" ? "manage_users" : "manage_departments") && (
        <>
          <button
            className="filter-button"
            disabled={kind === "employee" && protectedTarget(row)}
            onClick={() => open(kind, row)}
          >
            Edit
          </button>
          <button
            className="filter-button"
            disabled={
              busy ||
              (kind === "employee"
                ? protectedTarget(row) ||
                  (!user.platform_admin && row.id === user.id)
                : protectedDepartment(row))
            }
            onClick={() =>
              confirmAction(
                `${row.active ? "Deactivate" : "Activate"} ${row.full_name || row.name}? ${kind === "employee" ? "Existing sessions will be revoked." : "Deactivation removes inherited access; memberships are retained."}`,
                `/${kind === "employee" ? "employees" : "departments"}/${row.id}`,
                "PATCH",
                kind === "employee"
                  ? { active: !row.active }
                  : {
                      name: row.name,
                      code: row.code,
                      description: row.description,
                      manager_id: row.manager_id,
                      active: !row.active,
                    },
              )
            }
          >
            {row.active ? "Deactivate" : "Activate"}
          </button>
          {kind === "employee" && (
            <button
              className="filter-button"
              disabled={protectedTarget(row)}
              onClick={() => open("password", row)}
            >
              Reset password
            </button>
          )}
        </>
      )}
    </div>
  );
  return (
    <div className="access-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            {provider?.name || "SERVICE PROVIDER"} · INTERNAL ACCESS
          </div>
          <h1>Access Management</h1>
          <p>
            Employees and departments are independent of customer resource
            ownership.
          </p>
        </div>
        <button className="filter-button" disabled={busy} onClick={reload}>
          Refresh
        </button>
      </div>
      {onboarding && (
        <AccessOnboarding
          user={user}
          departments={departments}
          roles={roles}
          organizations={customers}
          onClose={() => setOnboarding(false)}
          onComplete={async () => {
            setOnboarding(false);
            await directories();
            await reload();
          }}
        />
      )}
      <div className="row-actions">
        <button
          disabled={busy || !can("manage_users")}
          onClick={() => setOnboarding(true)}
        >
          Guided Department → Employee → Permissions
        </button>
        <button
          disabled={busy || !can("manage_departments")}
          onClick={() => open("department")}
        >
          Create Department
        </button>
        <button
          disabled={busy || !can("manage_users")}
          onClick={() => open("employee")}
        >
          Create Employee
        </button>
      </div>
      <nav className="access-tabs" aria-label="Access Management sections">
        {TABS.filter(
          (t) => t !== "Access Audit" || hasPermission(user, "audit.view"),
        ).map((t) => (
          <button
            key={t}
            disabled={busy}
            className={`filter-button ${tab === t ? "active" : ""}`}
            onClick={() => {
              setLoading(true);
              setData({ items: [], total: 0 });
              detailEpoch.current++;
              setTab(t);
              setOffset(0);
              setSearch("");
              setSelected(null);
              setStatus("");
              setDepartment("");
              setRoleFilter("");
              // Clicking the already active tab still requests a fresh list;
              // unchanged React dependencies cannot trigger the fetch effect.
              if (t === tab) latestReload.current();
            }}
          >
            {t}
          </button>
        ))}
      </nav>
      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="info-box" role="status">
          {notice}
        </div>
      )}
      <section className="card access-table">
        <div className="resource-toolbar">
          <h2>{tab}</h2>
          <div className="access-filters">
            {["Employees", "Departments", "Roles & Permissions"].includes(
              tab,
            ) && (
              <input
                aria-label={`Search ${tab}`}
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setOffset(0);
                }}
                placeholder="Search name, code or employee ID"
              />
            )}
            {["Employees", "Departments"].includes(tab) && (
              <select
                aria-label="Account status filter"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setOffset(0);
                }}
              >
                <option value="">All statuses</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            )}
            {tab === "Employees" && (
              <select
                aria-label="Department filter"
                value={department}
                onChange={(e) => {
                  setDepartment(e.target.value);
                  setOffset(0);
                }}
              >
                <option value="">All departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            )}
            {tab === "Employees" && (
              <select
                aria-label="Role filter"
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setOffset(0);
                }}
              >
                <option value="">All roles</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            )}
            {tab === "Employees" && can("manage_users") && (
              <button
                className="primary-button"
                onClick={() => open("employee")}
              >
                Create employee
              </button>
            )}
            {tab === "Departments" && can("manage_departments") && (
              <button
                className="primary-button"
                onClick={() => open("department")}
              >
                Create department
              </button>
            )}
            {tab === "Roles & Permissions" &&
              can("manage_roles") &&
              can("manage_permissions") && (
                <button className="primary-button" onClick={() => open("role")}>
                  Create role
                </button>
              )}
          </div>
        </div>
        {loading ? (
          <p role="status">Loading {tab.toLowerCase()}…</p>
        ) : !data.items.length ? (
          <p className="state-panel">
            No matching records. Adjust the filters or create a record with the
            appropriate administrative permission.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {(tab === "Employees"
                    ? [
                        "Name",
                        "Username",
                        "Email",
                        "Employee ID / UUID",
                        "Departments",
                        "Assigned roles",
                        "Status",
                        "Actions",
                      ]
                    : tab === "Departments"
                      ? [
                          "Department",
                          "Code / UUID",
                          "Employees",
                          "Roles & customer scopes",
                          "Status",
                          "Actions",
                        ]
                      : tab === "Roles & Permissions"
                        ? [
                            "Role",
                            "Implemented permissions",
                            "Status",
                            "Actions",
                          ]
                        : [
                            "Timestamp",
                            "Actor UUID",
                            "Action",
                            "Target",
                            "Outcome",
                          ]
                  ).map((h) => (
                    <th key={h} scope="col">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.id}>
                    {tab === "Employees" && (
                      <>
                        <td>
                          <b>{row.full_name}</b>
                          {row.protected_administration &&
                            !row.platform_admin && (
                              <span className="mini-chip">
                                Reserved administration identity
                              </span>
                            )}
                          {row.platform_admin && (
                            <span className="mini-chip">
                              Protected platform administrator
                            </span>
                          )}
                        </td>
                        <td>
                          <code>{row.username}</code>
                        </td>
                        <td>{row.work_email || "—"}</td>
                        <td>
                          {row.employee_id || "—"}
                          <code className="access-uuid">{row.id}</code>
                        </td>
                        <td>
                          {row.departments
                            .filter((d) => d.active)
                            .map((d) => departmentName(d.id))
                            .join(", ") || "Unassigned"}
                        </td>
                        <td>
                          {row.roles
                            .map((r) => `${r.effect}: ${roleName(r.id)}`)
                            .join(", ") || "No direct roles"}
                        </td>
                        <td>
                          <Status active={row.active} />
                        </td>
                        <td>{actions(row, "employee")}</td>
                      </>
                    )}
                    {tab === "Departments" && (
                      <>
                        <td>
                          <b>{row.name}</b>
                          <small>
                            {row.description || "Internal department"}
                          </small>
                          {row.manager_id && (
                            <small>
                              Manager: {employeeName(row.manager_id)}
                            </small>
                          )}
                        </td>
                        <td>
                          {row.code || "—"}
                          <code className="access-uuid">{row.id}</code>
                        </td>
                        <td>{row.employee_count}</td>
                        <td>
                          {row.roles.map((r) => roleName(r.id)).join(", ") ||
                            "No roles"}
                          <small>
                            {row.customer_access
                              .map(
                                (g) =>
                                  `${customerName(g.organization_id)} (${roleName(g.role_id)})`,
                              )
                              .join(", ") || "No customer scope"}
                          </small>
                        </td>
                        <td>
                          <Status active={row.active} />
                        </td>
                        <td>{actions(row, "department")}</td>
                      </>
                    )}
                    {tab === "Roles & Permissions" && (
                      <>
                        <td>
                          <b>{row.name}</b>
                          <small>
                            {row.system
                              ? "Reviewed, immutable default"
                              : "Configurable role"}
                          </small>
                        </td>
                        <td>
                          <div className="chip-row">
                            {row.permissions.map((k) => (
                              <code className="mini-chip" key={k}>
                                {k}
                              </code>
                            ))}
                          </div>
                        </td>
                        <td>
                          <Status active={row.active} />
                        </td>
                        <td>
                          {!row.system &&
                            can("manage_roles") &&
                            can("manage_permissions") && (
                              <button
                                className="filter-button"
                                onClick={() => open("role", row)}
                              >
                                Edit role
                              </button>
                            )}
                        </td>
                      </>
                    )}
                    {tab === "Access Audit" && (
                      <>
                        <td>
                          <time>
                            {new Date(row.timestamp).toLocaleString()}
                          </time>
                        </td>
                        <td>
                          <code className="access-uuid">{row.actor_id}</code>
                        </td>
                        <td>{row.action}</td>
                        <td>
                          {row.target_type}
                          <code className="access-uuid">{row.target_id}</code>
                        </td>
                        <td>{row.outcome}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {tab !== "Roles & Permissions" && (
          <div className="access-pagination">
            <span>
              {data.total} records · {data.total ? offset + 1 : 0}–
              {Math.min(offset + PAGE, data.total)}
            </span>
            <button
              className="filter-button"
              disabled={loading || !offset}
              onClick={() => setOffset((v) => Math.max(0, v - PAGE))}
            >
              Previous
            </button>
            <button
              className="filter-button"
              disabled={loading || offset + PAGE >= data.total}
              onClick={() => setOffset((v) => v + PAGE)}
            >
              Next
            </button>
          </div>
        )}
      </section>
      {selected && (
        <section className="card access-table">
          <div className="resource-toolbar">
            <h2>
              {selected.full_name || selected.name} ·{" "}
              {selected.kind === "employee"
                ? "Effective access"
                : "Department members & permissions"}
            </h2>
            <button
              className="filter-button"
              onClick={() => {
                detailEpoch.current++;
                setSelected(null);
              }}
            >
              Close details
            </button>
          </div>
          <code className="access-uuid">Immutable UUID: {selected.id}</code>
          {detailLoading && (
            <p role="status">
              Loading{" "}
              {selected.kind === "department"
                ? "department members"
                : "effective permissions"}
              …
            </p>
          )}
          {detailError && (
            <p className="error-box" role="alert">
              {detailError}
            </p>
          )}
          {can("manage_roles") && (
            <button
              className="filter-button"
              onClick={() => open("assignment", selected)}
            >
              Assign role
            </button>
          )}
          <h3>Direct role assignments</h3>
          {selected.roles.map((r) => (
            <p key={r.assignment_id}>
              {r.effect || "ALLOW"} · {roleName(r.id)}{" "}
              {can("manage_roles") && (
                <button
                  className="danger-button"
                  disabled={busy}
                  onClick={() =>
                    confirmAction(
                      "Revoke this role and its paired customer grants?",
                      `/${selected.kind === "employee" ? "employees" : "departments"}/${selected.id}/roles/${r.assignment_id}`,
                      "DELETE",
                    )
                  }
                >
                  Remove role
                </button>
              )}
            </p>
          ))}
          {selected.kind === "employee" ? (
            <>
              <h3>Department assignment</h3>
              {can("manage_users") && can("manage_departments") && (
                <button
                  className="filter-button"
                  onClick={() => open("employee-department", selected)}
                >
                  Assign department
                </button>
              )}
              {selected.departments
                .filter((d) => d.active)
                .map((d) => (
                  <p key={d.membership_id}>
                    {departmentName(d.id)}{" "}
                    {can("manage_users") && can("manage_departments") && (
                      <button
                        className="danger-button"
                        onClick={() =>
                          confirmAction(
                            "Remove this department membership?",
                            `/departments/${d.id}/members/${selected.id}`,
                            "DELETE",
                          )
                        }
                      >
                        Remove membership
                      </button>
                    )}
                  </p>
                ))}
              {!detailLoading && !detailError && (
                <Effective value={effective} customers={customers} />
              )}
            </>
          ) : (
            <>
              {can("manage_users") && can("manage_departments") && (
                <button
                  className="filter-button"
                  disabled={busy || detailLoading || !!detailError}
                  onClick={() => open("member", selected)}
                >
                  Add employee
                </button>
              )}
              <h3>Members</h3>
              {!detailLoading &&
                !detailError &&
                (members.length ? (
                  members.map((m) => (
                    <p key={m.id}>
                      <button
                        className="filter-button"
                        onClick={() => inspectEmployee(m)}
                      >
                        {m.full_name} · Review effective permissions
                      </button>{" "}
                      {can("manage_users") && can("manage_departments") && (
                        <button
                          className="danger-button"
                          onClick={() =>
                            confirmAction(
                              "Remove this employee from the department?",
                              `/departments/${selected.id}/members/${m.id}`,
                              "DELETE",
                            )
                          }
                        >
                          Remove employee
                        </button>
                      )}
                    </p>
                  ))
                ) : (
                  <p>No employees assigned.</p>
                ))}
              <h3>Permission summary</h3>
              {selected.roles.map((a) => (
                <div key={a.id}>
                  <b>{roleName(a.id)}</b>
                  <div className="chip-row">
                    {roles
                      .find((r) => r.id === a.id)
                      ?.permissions.map((k) => (
                        <code className="mini-chip" key={k}>
                          {k}
                        </code>
                      ))}
                  </div>
                  <p className="muted">
                    Organization scopes:{" "}
                    {selected.customer_access
                      .filter((g) => g.role_id === a.id)
                      .map((g) => customerName(g.organization_id))
                      .join(", ") ||
                      "None — operational permissions remain inactive."}
                  </p>
                </div>
              ))}
            </>
          )}
        </section>
      )}
      {dialog && (
        <Dialog
          title={
            dialog.kind === "assignment"
              ? "Assign role"
              : dialog.kind === "employee-department"
                ? "Assign employee department"
                : dialog.kind === "member"
                  ? "Assign employee to department"
                  : dialog.kind === "password"
                    ? "Reset employee password"
                    : `${dialog.row.id ? "Edit" : "Create"} ${dialog.kind}`
          }
          onClose={() => !busy && setDialog(null)}
        >
          <form className="resource-form" onSubmit={save}>
            {error && (
              <div className="error-box" role="alert">
                {error}
              </div>
            )}
            {dialog.kind === "employee" && (
              <>
                <Field label="Full name">
                  <input
                    required
                    maxLength={160}
                    value={draft.full_name}
                    onChange={(e) => change("full_name", e.target.value)}
                  />
                </Field>
                <Field label="Username">
                  <input
                    required
                    disabled={!!dialog.row.id}
                    maxLength={120}
                    value={draft.username}
                    onChange={(e) => change("username", e.target.value)}
                  />
                </Field>
                <Field label="Employee ID">
                  <input
                    maxLength={80}
                    value={draft.employee_id}
                    onChange={(e) => change("employee_id", e.target.value)}
                  />
                </Field>
                <Field label="Work email">
                  <input
                    type="email"
                    value={draft.work_email}
                    onChange={(e) => change("work_email", e.target.value)}
                  />
                </Field>
                {!dialog.row.id && (
                  <Field label="Department (exactly one)">
                    <select
                      required
                      value={draft.department_id}
                      onChange={(e) => change("department_id", e.target.value)}
                    >
                      <option value="">Select existing department</option>
                      {departments
                        .filter((d) => d.active)
                        .map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                    </select>
                  </Field>
                )}
                {!dialog.row.id && (
                  <Field label="Initial password">
                    <input
                      type="password"
                      autoComplete="new-password"
                      required
                      minLength={12}
                      maxLength={1024}
                      value={draft.password}
                      onChange={(e) => change("password", e.target.value)}
                    />
                  </Field>
                )}
                {user.platform_admin && (
                  <label className="access-checkbox">
                    <input
                      type="checkbox"
                      checked={draft.platform_admin}
                      onChange={(e) =>
                        change("platform_admin", e.target.checked)
                      }
                    />{" "}
                    Protected platform administrator
                  </label>
                )}
                <p className="muted">
                  Employee identity is immutable. New employees have no customer
                  access until explicit assignments are made.
                </p>
              </>
            )}
            {dialog.kind === "department" && (
              <>
                <Field label="Department name">
                  <input
                    required
                    maxLength={160}
                    value={draft.name}
                    onChange={(e) => change("name", e.target.value)}
                  />
                </Field>
                <Field label="Department code">
                  <input
                    maxLength={40}
                    value={draft.code}
                    onChange={(e) => change("code", e.target.value)}
                  />
                </Field>
                <Field label="Description">
                  <textarea
                    maxLength={1000}
                    value={draft.description}
                    onChange={(e) => change("description", e.target.value)}
                  />
                </Field>
                <Field label="Department manager">
                  <select
                    value={draft.manager_id}
                    onChange={(e) => change("manager_id", e.target.value)}
                  >
                    <option value="">No manager</option>
                    {people.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.full_name}
                      </option>
                    ))}
                  </select>
                </Field>
                <label className="access-checkbox">
                  <input
                    type="checkbox"
                    checked={draft.active}
                    onChange={(e) => change("active", e.target.checked)}
                  />{" "}
                  Active department
                </label>
                <p className="muted">
                  Manager is descriptive metadata. It grants no permissions.
                  Deactivation preserves memberships and audit history.
                </p>
              </>
            )}
            {dialog.kind === "password" && (
              <>
                <Field label="New password">
                  <input
                    autoComplete="new-password"
                    type="password"
                    required
                    minLength={12}
                    maxLength={1024}
                    value={draft.new_password}
                    onChange={(e) => change("new_password", e.target.value)}
                  />
                </Field>
                <p className="info-box">
                  The password is hashed server-side. Saving revokes all
                  employee sessions.
                </p>
              </>
            )}
            {dialog.kind === "employee-department" && (
              <>
                <Field label="Department">
                  <select
                    required
                    value={draft.department_id}
                    onChange={(e) => change("department_id", e.target.value)}
                  >
                    <option value="">Select department</option>
                    {departments
                      .filter(
                        (d) =>
                          d.active &&
                          !dialog.row.departments.some(
                            (m) => m.active && m.id === d.id,
                          ),
                      )
                      .map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                          {!d.active && " (inactive)"}
                        </option>
                      ))}
                  </select>
                </Field>
                <h3>Inherited access preview</h3>
                {departments
                  .find((d) => d.id === draft.department_id)
                  ?.roles.map((a) => (
                    <p key={a.id}>
                      {roleName(a.id)} ·{" "}
                      {roles.find((r) => r.id === a.id)?.permissions.join(", ")}
                    </p>
                  ))}
                <p>
                  Paired customer scopes:{" "}
                  {departments
                    .find((d) => d.id === draft.department_id)
                    ?.customer_access.map(
                      (g) =>
                        `${customerName(g.organization_id)} (${roleName(g.role_id)})`,
                    )
                    .join(", ") || "None"}
                </p>
                <p className="muted">
                  Inactive departments grant no access. Existing
                  employee-specific denies continue to narrow inherited
                  permissions.
                </p>
              </>
            )}
            {dialog.kind === "member" && (
              <>
                <Field label="Employee">
                  <select
                    required
                    value={draft.user_id}
                    onChange={(e) => change("user_id", e.target.value)}
                  >
                    <option value="">Select employee</option>
                    {people
                      .filter((p) => !members.some((m) => m.id === p.id))
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.full_name} ({p.username})
                        </option>
                      ))}
                  </select>
                </Field>
                <p className="info-box">
                  This replaces the employee’s current department. The employee
                  inherits this department’s roles and paired organization
                  scopes. Review the department permission summary before
                  saving.
                </p>
              </>
            )}
            {dialog.kind === "assignment" && (
              <>
                <Field label="Role">
                  <select
                    required
                    value={draft.role_id}
                    onChange={(e) => change("role_id", e.target.value)}
                  >
                    <option value="">Select role</option>
                    {roles
                      .filter(
                        (r) => r.active && r.code !== "platform-administrator",
                      )
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name}
                        </option>
                      ))}
                  </select>
                </Field>
                {dialog.row.kind === "employee" && (
                  <Field label="Assignment effect">
                    <select
                      value={draft.effect}
                      onChange={(e) => change("effect", e.target.value)}
                    >
                      <option value="ALLOW">Allow role</option>
                      <option value="DENY">
                        Restrict these permissions across inherited sources
                      </option>
                    </select>
                  </Field>
                )}
                <h3>Permission preview</h3>
                <div className="chip-row">
                  {roles
                    .find((r) => r.id === draft.role_id)
                    ?.permissions.map((k) => (
                      <code className="mini-chip" key={k}>
                        {k}
                      </code>
                    ))}
                </div>
                <p className="info-box">
                  Operational permissions require a separate, paired customer
                  grant. Access administration permissions apply globally within
                  the service provider. Employee DENY assignments remove the
                  selected permission keys from inherited access.
                </p>
              </>
            )}
            {dialog.kind === "role" && (
              <>
                <Field label="Role name">
                  <input
                    required
                    maxLength={160}
                    value={draft.name}
                    onChange={(e) => change("name", e.target.value)}
                  />
                </Field>
                <Field label="Role description">
                  <textarea
                    maxLength={1000}
                    value={draft.description}
                    onChange={(e) => change("description", e.target.value)}
                  />
                </Field>
                <label className="access-checkbox">
                  <input
                    type="checkbox"
                    checked={draft.active}
                    onChange={(e) => change("active", e.target.checked)}
                  />{" "}
                  Active role
                </label>
                <h3>Implemented permission matrix</h3>
                <p className="muted">
                  Only supported backend actions are listed. Restricted
                  administrative permissions require protected platform
                  delegation.
                </p>
                <div className="access-permission-matrix">
                  {[...new Set(catalog.map((p) => p.module))].map((module) => (
                    <fieldset key={module}>
                      <legend>{module}</legend>
                      {catalog
                        .filter((p) => p.module === module)
                        .map((p) => (
                          <label
                            className="access-checkbox"
                            key={p.key}
                            title={p.description}
                          >
                            <input
                              type="checkbox"
                              disabled={!user.platform_admin && !p.delegable}
                              checked={draft.permissions.includes(p.key)}
                              onChange={(e) =>
                                change(
                                  "permissions",
                                  e.target.checked
                                    ? [...draft.permissions, p.key]
                                    : draft.permissions.filter(
                                        (k) => k !== p.key,
                                      ),
                                )
                              }
                            />
                            <span>{p.action}</span>
                          </label>
                        ))}
                    </fieldset>
                  ))}
                </div>
                <p className="info-box">
                  Saving replaces this role’s permission set for all assigned
                  employees and departments immediately. Customer boundaries
                  remain paired with their existing grants.
                </p>
              </>
            )}
            <div className="form-footer">
              <button
                className="filter-button"
                type="button"
                disabled={busy}
                onClick={() => setDialog(null)}
              >
                Cancel
              </button>
              <button className="primary-button" disabled={busy}>
                {busy ? "Checking…" : "Save changes"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </div>
  );
}
