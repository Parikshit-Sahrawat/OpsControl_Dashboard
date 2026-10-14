import { useEffect, useState } from "react";
import { control } from "../controlPlane";
// Discovery-only provider identities are retained without pretending they are
// installable Compute Instances or minting new VM/resource relationships.
export default function ImportedDiscoveryInventory({
  organizationId,
  collectorOrganizations = [],
  authorizationRevision,
}) {
  const [items, setItems] = useState(null),
    [error, setError] = useState(""),
    [search, setSearch] = useState(""),
    [revision, setRevision] = useState(0);
  useEffect(() => {
    let live = true;
    setItems(null);
    setError("");
    const q = new URLSearchParams({ limit: "1000" });
    if (organizationId) q.append("organization_id", organizationId);
    control("/api/v1/resource-management/data-sources?" + q)
      .then(async (sources) => {
        const retained = sources.filter((s) => s.source_type === "AWS_EKS");
        const registrations = new Map();
        const readable = retained.filter((s) =>
          collectorOrganizations.includes(s.organization_id),
        );
        for (let i = 0; i < readable.length; i += 20) {
          const batch = readable.slice(i, i + 20);
          const params = new URLSearchParams({ limit: "1000" });
          batch.forEach((s) => params.append("data_source_id", s.id));
          const rows = await control(
            "/api/v1/resource-management/collectors?" + params,
          );
          rows.forEach((c) =>
            registrations.set(
              c.data_source_id,
              (registrations.get(c.data_source_id) || 0) + 1,
            ),
          );
        }
        if (live)
          setItems(
            retained.map((s) => ({
              ...s,
              configuration_count: collectorOrganizations.includes(
                s.organization_id,
              )
                ? registrations.get(s.id) || 0
                : null,
            })),
          );
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [
    organizationId,
    revision,
    collectorOrganizations.join(","),
    authorizationRevision,
  ]);
  const rows = (items || []).filter((s) =>
    (s.name + " " + JSON.stringify(s.connection_config))
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <section className="card">
      <div className="page-heading">
        <h3>Imported discovery inventory</h3>
        <button disabled={!items} onClick={() => setRevision((v) => v + 1)}>
          Refresh discovery inventory
        </button>
      </div>
      <p>
        Read-only provider discoveries retain their original identity. EKS
        discovery does not imply host-agent installation or operational health.
      </p>
      <label>
        Search imported discovery
        <input value={search} onChange={(e) => setSearch(e.target.value)} />
      </label>
      {error && <p role="alert">{error}</p>}
      {!items && !error && (
        <p role="status">Loading authorized discovery records…</p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Discovered resource</th>
              <th>Provider / region</th>
              <th>Recorded state</th>
              <th>Agent capability</th>
              <th>Retained configurations</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.connection_config?.cluster_names?.length === 1
                    ? s.connection_config.cluster_names[0]
                    : s.name}
                  <small>{s.name}</small>
                  <small>{s.id}</small>
                </td>
                <td>EKS · {s.connection_config?.region || "Unspecified"}</td>
                <td>{s.status || "UNKNOWN"}</td>
                <td>DISCOVERY ONLY</td>
                <td>{s.configuration_count ?? "Restricted"}</td>
                <td>
                  <button
                    disabled
                    title="Provider discovery scope is managed through its authorized discovery configuration API"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {items && !rows.length && (
        <p>No imported EKS discovery records match this authorized scope.</p>
      )}
      <small>
        Discovery source lookup is bounded to 1,000 authorized Data Sources;
        Collector requests contain at most 20 source identifiers.
      </small>
    </section>
  );
}
