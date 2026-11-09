import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../src/pages/ETLJobs.jsx", import.meta.url), "utf8");

test("ETL Clear filters resets all four selectors to their unfiltered defaults", () => {
  const clearButton = source.match(/onClick=\{\(\) => \{([\s\S]*?)\}\}\s*>\s*Clear filters/);
  assert.ok(clearButton, "Clear filters button handler must exist");
  const handler = clearButton[1];
  for (const call of [
    'setFilter("All")',
    'setEnvironment("All")',
    'setExecutionType("All")',
    'setQuery("")',
  ]) {
    assert.ok(handler.includes(call), `Clear filters must call ${call}`);
  }
});

test("ETL environment filter includes an all-environments option", () => {
  assert.match(source, /const environments = useMemo\([\s\S]*?"All"/);
  assert.match(source, /environment === "All" \|\| job\.environment === environment/);
});
