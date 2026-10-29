// Operational source identities only; historical telemetry labels are retained.
const aliases = new Set(["kubernetes", "k8s", "eks", "aks", "gke", "openshift",
  "k3s", "k0s", "microk8s", "rke", "rke2", "awseks", "amazoneks", "azureaks",
  "googlegke", "gcpgke", "amazonelasticcontainerserviceforkubernetes"]);
export function isExcludedPlatform(value) {
  if (typeof value !== "string") return false;
  const words = value.toLowerCase().split(/[^a-z0-9]+/);
  const compact = value.toLowerCase().replace(/[^a-z0-9]/g, "");
  return words.some(word => aliases.has(word)) || aliases.has(compact)
    || compact.includes("kubernetes") || compact.includes("openshift");
}
