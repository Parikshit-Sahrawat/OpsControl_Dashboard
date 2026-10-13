import { authHeaders } from "./auth";
const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export async function control(path, method = "GET", payload, options = {}) {
  const response = await fetch(base + path, {
    method,
    signal: options.signal,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
  if (!response.ok) {
    let message = "Request failed";
    try {
      message = (await response.json()).detail || message;
    } catch {}
    throw new Error(
      typeof message === "string" ? message : JSON.stringify(message),
    );
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
export async function downloadPackage(platform) {
  const response = await fetch(
    base + "/api/v1/agent-control/packages/" + platform,
    { headers: authHeaders() },
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Package unavailable");
  }
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = "opscontrol-agent-" + platform + ".zip";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
