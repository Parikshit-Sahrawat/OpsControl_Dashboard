import { useEffect, useRef, useState } from "react";
import { control } from "../controlPlane";
import useDialogFocus from "../components/useDialogFocus";
import { hasPermission } from "../permissions";
export default function AccessOnboarding({
  user,
  departments,
  roles,
  organizations,
  onClose,
  onComplete,
}) {
  const [step, setStep] = useState(1),
    [department, setDepartment] = useState(""),
    [newDepartment, setNewDepartment] = useState(""),
    [code, setCode] = useState(""),
    [employee, setEmployee] = useState({
      username: "",
      full_name: "",
      password: "",
      work_email: "",
    }),
    [employeeId, setEmployeeId] = useState(""),
    [search, setSearch] = useState(""),
    [people, setPeople] = useState([]),
    [role, setRole] = useState(""),
    [effective, setEffective] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [peopleLoading, setPeopleLoading] = useState(false);
  const ref = useRef(null);
  useDialogFocus(ref, true, onClose);
  const [options, setOptions] = useState(departments);
  useEffect(
    () =>
      setOptions((previous) => [
        ...new Map(
          [...previous, ...departments].map((d) => [d.id, d]),
        ).values(),
      ]),
    [departments],
  );
  const action = async (fn) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    let live = true;
    if (step === 3) {
      setPeopleLoading(true);
      setError("");
      control(
        "/api/v1/access/employees?limit=50&search=" +
          encodeURIComponent(search) +
          "&department_id=" + encodeURIComponent(department),
      )
        .then((data) => live && setPeople(data.items))
        .catch((e) => {
          if (live) {
            setPeople([]);
            setError(e.message);
          }
        })
        .finally(() => live && setPeopleLoading(false));
    }
    return () => {
      live = false;
    };
  }, [step, search, department]);
  useEffect(() => {
    let live = true;
    setEffective(null);
    if (employeeId)
      control(
        "/api/v1/access/employees/" + employeeId + "/effective-permissions",
      )
        .then((v) => live && setEffective(v))
        .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [employeeId]);
  return (
    <div className="modal-backdrop">
      <section
        className="modal access-dialog"
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label="Department Employee Permissions onboarding"
      >
        <div className="modal-header">
          <h2>Department → Employee → Permissions</h2>
          <button
            disabled={busy}
            onClick={onClose}
            aria-label="Close onboarding"
          >
            ×
          </button>
        </div>
        <nav className="access-tabs">
          {["Department", "Employee", "Permissions"].map((label, i) => (
            <button
              type="button"
              key={label}
              disabled={busy || (i > 0 && !department)}
              aria-current={step === i + 1 ? "step" : undefined}
              onClick={() => setStep(i + 1)}
            >
              {i + 1}. {label}
            </button>
          ))}
        </nav>
        {error && <p role="alert">{error}</p>}
        {step === 1 && (
          <div className="resource-form">
            <label className="form-field">
              <span>Select existing department</span>
              <select
                aria-label="Select existing department"
                value={department}
                onChange={(e) => { setDepartment(e.target.value); setEmployeeId(""); }}
              >
                <option value="">Select department</option>
                {options
                  .filter((d) => d.active)
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
              </select>
            </label>
            <h3>Or create a department</h3>
            <label className="form-field">
              <span>Department name</span>
              <input
                value={newDepartment}
                onChange={(e) => setNewDepartment(e.target.value)}
              />
            </label>
            <label className="form-field">
              <span>Optional department code</span>
              <input value={code} onChange={(e) => setCode(e.target.value)} />
            </label>
            <button
              disabled={
                busy ||
                !newDepartment ||
                !hasPermission(user, "access.manage_departments")
              }
              onClick={() =>
                action(async () => {
                  const d = await control(
                    "/api/v1/access/departments",
                    "POST",
                    {
                      name: newDepartment,
                      code: code || null,
                      description: "",
                      active: true,
                    },
                  );
                  setOptions((o) => [...o, d]);
                  setDepartment(d.id);
                  setNewDepartment("");
                })
              }
            >
              Create Department
            </button>
            <button
              className="primary-button"
              disabled={busy || !department}
              onClick={() => setStep(2)}
            >
              Continue to Employee
            </button>
            <button type="button" disabled={busy || !department} onClick={() => setStep(3)}>
              Find existing employee in this department
            </button>
          </div>
        )}
        {step === 2 && (
          <form
            className="resource-form"
            onSubmit={(e) => {
              e.preventDefault();
              action(async () => {
                const p = await control("/api/v1/access/employees", "POST", {
                  ...employee,
                  work_email: employee.work_email || null,
                  department_id: department,
                });
                setEmployeeId(p.id);
                setEmployee({
                  username: "",
                  full_name: "",
                  password: "",
                  work_email: "",
                });
                setStep(3);
              });
            }}
          >
            <p>
              Exactly one existing department:{" "}
              {options.find((d) => d.id === department)?.name}
            </p>
            {[
              ["full_name", "Full name"],
              ["username", "Username"],
              ["work_email", "Work email"],
              ["password", "Initial password"],
            ].map(([key, label]) => (
              <label className="form-field" key={key}>
                <span>{label}</span>
                <input
                  required={key !== "work_email"}
                  type={
                    key === "password"
                      ? "password"
                      : key === "work_email"
                        ? "email"
                        : "text"
                  }
                  minLength={key === "password" ? 12 : undefined}
                  autoComplete={key === "password" ? "new-password" : undefined}
                  value={employee[key]}
                  onChange={(e) =>
                    setEmployee((d) => ({ ...d, [key]: e.target.value }))
                  }
                />
              </label>
            ))}
            <button
              className="primary-button"
              disabled={busy || !hasPermission(user, "access.manage_users")}
            >
              Create Employee
            </button>
          </form>
        )}
        {step === 3 && (
          <div className="resource-form">
            <label className="form-field">
              <span>Search existing employees</span>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Name, username or employee ID"
              />
            </label>
            <div className="access-employee-results" aria-label="Matching employees">
              {people.filter((p) => p.active).map((person) => (
                <button type="button" key={person.id} aria-pressed={employeeId === person.id}
                  onClick={() => setEmployeeId(person.id)}>
                  {person.full_name} <small>{person.username}</small>
                </button>
              ))}
            </div>
            {employeeId && <p role="status">Selected employee: {people.find((person) => person.id === employeeId)?.full_name || employeeId}</p>}
            {peopleLoading && <p role="status">Searching employees…</p>}
            {!peopleLoading && !people.length && <p>No matching employees.</p>}
            <label className="form-field">
              <span>Role / configured permissions</span>
              <select
                aria-label="Role / configured permissions"
                value={role}
                onChange={(e) => {
                  setRole(e.target.value);
                }}
              >
                <option value="">Select existing role</option>
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
            </label>
            <p>
              {roles.find((r) => r.id === role)?.permissions?.join(", ") ||
                "Role permissions are configured in Roles & Permissions."}
            </p>
            <button
              disabled={
                busy ||
                !employeeId ||
                !role ||
                !hasPermission(user, "access.manage_roles")
              }
              onClick={() =>
                action(async () => {
                  if (
                    !window.confirm(
                      "Assign the displayed role to this employee? Customer access remains limited by existing grants.",
                    )
                  )
                    return;
                  await control(
                    "/api/v1/access/employees/" + employeeId + "/roles",
                    "POST",
                    { role_id: role, effect: "ALLOW" },
                  );
                  setEffective(
                    await control(
                      "/api/v1/access/employees/" +
                        employeeId +
                        "/effective-permissions",
                    ),
                  );
                })
              }
            >
              Assign Role
            </button>
            <p className="muted">
              This workflow manages internal role assignments. Existing
              customer-scoped grants remain enforced by the backend;
              customer-grant administration is handled through the authorized
              access API.
            </p>
            <h3>Effective permissions</h3>
            {effective ? (
              <div className="access-effective">
                <p>
                  {effective.disabled
                    ? "Disabled account — no usable access."
                    : effective.break_glass
                      ? "Protected platform administration."
                      : "Default deny; only displayed permissions and existing customer grants apply."}
                </p>
                <div className="chip-row">
                  {effective.permissions?.map((key) => (
                    <code className="mini-chip" key={key}>
                      {key}
                    </code>
                  ))}
                </div>
                <h4>Inherited and direct assignments</h4>
                {(effective.inherited_and_direct || []).map((source, i) => (
                  <p key={i}>
                    {source.source} · {source.role} ·{" "}
                    {source.scope === "provider"
                      ? "Service provider"
                      : organizations.find(
                          (org) => org.id === source.customer_id,
                        )?.name || source.customer_id}
                  </p>
                ))}
                <h4>Existing organization scopes</h4>
                {Object.entries(effective.customer_permissions || {}).map(
                  ([id, keys]) => (
                    <p key={id}>
                      {organizations.find((org) => org.id === id)?.name || id}:{" "}
                      {keys.join(", ")}
                    </p>
                  ),
                )}
              </div>
            ) : (
              <p>
                Select an employee to review direct and inherited permissions.
              </p>
            )}
            <button disabled={busy} onClick={onComplete}>
              Finish
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
