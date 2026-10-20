import assert from "node:assert/strict";
import { readAllPages } from "../src/pagination.js";
const scope = { current: true };
const pages = [
  { items: [{ id: "a" }, { id: "b" }], total: 3, offset: 0, has_more: true },
  { items: [{ id: "c" }], total: 3, offset: 2, has_more: false },
];
assert.deepEqual(await readAllPages(async (n) => pages[n ? 1 : 0]), [
  { id: "a" },
  { id: "b" },
  { id: "c" },
]);
assert.deepEqual(
  await readAllPages(async () => ({
    items: [],
    total: 0,
    offset: 0,
    has_more: false,
  })),
  [],
);
for (const bad of [
  { items: [{ id: "a" }], total: 3, offset: 2, has_more: false },
  { items: [{ id: "c" }], total: 4, offset: 2, has_more: false },
  { items: [], total: 3, offset: 2, has_more: true },
  { items: [], total: 3, offset: 2, has_more: false },
  { items: [{ id: "c" }], total: 3, offset: 3, has_more: false },
])
  await assert.rejects(readAllPages(async (n) => (n ? bad : pages[0])));
await assert.rejects(
  readAllPages(
    async () => {
      scope.current = false;
      return pages[0];
    },
    () => scope.current,
  ),
  /access changed/,
);
await assert.rejects(
  readAllPages(
    async () => assert.fail("must not fetch revoked scope"),
    () => false,
  ),
  /access changed/,
);
console.log(
  "Pagination traversal, duplicate, mutation, incomplete and scope-change regressions passed",
);
