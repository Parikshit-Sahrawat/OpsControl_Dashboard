import test from "node:test";
import assert from "node:assert/strict";
import { scopeHeaders } from "./explicit_scope.mjs";
test("owned browser clients explicitly select a UUID snapshot and empty stays empty", async () => {
  for (const ids of [[], ["customer-a", "customer-b"]]) {
    const request = {
      get: async (url, options) => {
        assert.equal(url, "http://local/api/v1/auth/customer-scope");
        assert.equal(options.headers.Authorization, "Bearer employee");
        return { ok: () => true, json: async () => ids.map((id) => ({ id })) };
      },
    };
    const headers = await scopeHeaders(request, "http://local", "employee");
    assert.equal(headers["X-OpsControl-Customers"], ids.join(","));
    assert.notEqual(headers["X-OpsControl-Customers"], "ALL");
  }
});
test("failed customer lookup cannot fall back to unrestricted operational requests", async () => {
  const request = { get: async () => ({ ok: () => false, status: () => 403 }) };
  await assert.rejects(
    scopeHeaders(request, "http://local", "revoked"),
    /snapshot unavailable: 403/,
  );
});
