import { useEffect, useRef, useState } from "react";
import { control } from "../controlPlane";
import { params, binding, requestGeneration } from "./contracts";

export default function usePipelineFeed(path, enrich = false) {
  const [state, setState] = useState({
    key: null,
    data: null,
    error: null,
    loading: false,
    updatedAt: null,
  });
  const [revision, setRevision] = useState(0),
    generation = useRef(requestGeneration());
  useEffect(() => {
    const refresh = () => setRevision((v) => v + 1);
    window.addEventListener("pipeline-refresh", refresh);
    return () => window.removeEventListener("pipeline-refresh", refresh);
  }, []);
  useEffect(() => {
    const version = generation.current.next(),
      controller = new AbortController();
    let pending = false;
    const accepted = () => generation.current.accepts(version);
    const load = async () => {
      if (!path || pending) return;
      pending = true;
      setState((old) => ({
        ...old,
        key: path,
        data: old.key === path ? old.data : null,
        error: null,
        loading: true,
      }));
      try {
        const data = await control(path, "GET", undefined, {
          signal: controller.signal,
        });
        if (!accepted()) return;
        setState({
          key: path,
          data,
          error: null,
          loading: false,
          updatedAt: Date.now(),
        });
        if (enrich && data.items?.length) {
          // Inventory is usable immediately; bound concurrency keeps enrichment from
          // exhausting the API pool or holding the entire list behind one slow source.
          let next = 0;
          const integrations = new Map();
          const worker = async () => {
            while (next < data.items.length && accepted()) {
              const r = data.items[next++],
                id = r.configuration?.pipeline_integration_id;
              try {
                const observed = await control(
                  "/api/v1/unified/domain-state/ETL?" +
                    params([r.organization_id], r.environment, {
                      resource_id: r.id,
                      limit: 1,
                    }),
                  "GET",
                  undefined,
                  { signal: controller.signal },
                );
                if (id && !integrations.has(id))
                  integrations.set(
                    id,
                    control(
                      "/api/v1/data-pipelines/integrations/" + id,
                      "GET",
                      undefined,
                      { signal: controller.signal },
                    ).catch(() => null),
                  );
                const integration = id ? await integrations.get(id) : null;
                if (accepted())
                  setState((old) => ({
                    ...old,
                    data: {
                      ...old.data,
                      items: old.data.items.map((item) =>
                        item.id === r.id
                          ? {
                              ...item,
                              ...observed.items?.[0],
                              binding: binding(r, integration),
                              bindingUnavailable: Boolean(id && !integration),
                            }
                          : item,
                      ),
                    },
                  }));
              } catch (error) {
                if (accepted() && error.name !== "AbortError")
                  setState((old) => ({
                    ...old,
                    data: {
                      ...old.data,
                      items: old.data.items.map((item) =>
                        item.id === r.id
                          ? { ...item, observationUnavailable: true }
                          : item,
                      ),
                    },
                  }));
              }
            }
          };
          await Promise.all([worker(), worker(), worker()]);
        }
      } catch (error) {
        if (accepted() && error.name !== "AbortError")
          setState((old) => ({
            ...old,
            key: path,
            data: [401, 403].includes(error.status) ? null : old.data,
            error,
            loading: false,
          }));
      } finally {
        pending = false;
      }
    };
    if (path) load();
    const timer = path ? setInterval(load, 30000) : null;
    return () => {
      generation.current.invalidate();
      controller.abort();
      if (timer) clearInterval(timer);
    };
  }, [path, enrich, revision]);
  const current =
    state.key === path
      ? state
      : { data: null, error: null, loading: Boolean(path), updatedAt: null };
  return {
    ...current,
    stale: Boolean(
      current.data && (current.error || Date.now() - current.updatedAt > 60000),
    ),
    refresh: () => setRevision((v) => v + 1),
  };
}
