// Controlled browser probes select an authorized UUID snapshot, never implicit ALL.
export async function scopeHeaders(request, base, token) {
  const headers = { Authorization: "Bearer " + token };
  const response = await request.get(base + "/api/v1/auth/customer-scope", {
    headers,
  });
  if (!response.ok())
    throw Error(
      "Authorized customer snapshot unavailable: " + response.status(),
    );
  const customers = await response.json();
  return {
    ...headers,
    "X-OpsControl-Customers": customers.map((c) => c.id).join(","),
  };
}
