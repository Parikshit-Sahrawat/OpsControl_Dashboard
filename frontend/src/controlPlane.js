import { authHeaders } from "./auth";
const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export async function control(path, method = "GET", payload, options = {}) {
  const response = await fetch(base + path, {
    method,
    signal: options.signal,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.customerIds
        ? { "X-OpsControl-Customers": options.customerIds.join(",") }
        : {}),
    },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
  if (!response.ok) {
    let message = "Request failed";
    try {
      message = (await response.json()).detail || message;
    } catch {}
    const error = new Error(
      typeof message === "string"
        ? message
        : message?.message ||
          (Array.isArray(message)
            ? message.map((item) => item.msg || "Invalid request").join("; ")
            : "Evidence requirements are not satisfied"),
    );
    error.status = response.status;
    error.detail = message;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
export function downloadText(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const methodDefaults = {
  HOST_METRICS: {
    interval_seconds: 30,
    scrapers: ["cpu", "memory", "disk", "filesystem", "network"],
  },
  SERVICES: { services: [], processes: [], interval_seconds: 30 },
  SYSLOG_RECEIVER: {
    bind: "127.0.0.1",
    port: 1514,
    protocol: "TCP",
    format: "RFC5424",
    allow_remote: false,
    tls_certificate: null,
    tls_key_ref: null,
    client_ca: null,
  },
  FILE_LOG: {
    source: "FILE",
    paths: [],
    exclusions: [],
    format: "TEXT",
    start_at: "end",
  },
  METRIC_SCRAPE: {
    targets: [],
    timeout_seconds: 10,
    metric_include: [],
    metric_exclude: [],
    labels: {},
    interval_seconds: 30,
    path: "/metrics",
    tls: false,
  },
  OTLP_RECEIVER: {
    bind: "127.0.0.1",
    protocol: "HTTP",
    port: 4318,
    signals: ["Logs"],
    allow_remote: false,
  },
};
export async function packageAvailability() {
  return control("/api/v1/agent-control/packages/availability");
}

export async function downloadPackage(platform) {
  if (!["linux", "windows"].includes(platform)) {
    throw new Error("Unsupported agent platform");
  }
  const response = await fetch(
    base + "/api/v1/agent-control/packages/" + platform,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!response.ok) {
    let detail = "Agent installer unavailable";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // Preserve an actionable message when the server did not return JSON.
    }
    throw new Error(`Agent download failed (HTTP ${response.status}): ${detail}`);
  }
  const filename = platform === "windows"
    ? "opscontrol-agent-windows.exe"
    : "opscontrol-agent-linux.zip";
  const blob = await response.blob();
  if (blob.size === 0) throw new Error("Agent package is empty; contact the administrator");
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
