// Traverse verified offset-page contracts. Never silently present a truncated
// chooser/list as complete, or combine pages from different authorization scopes.
export async function readAllPages(readPage, isCurrent = () => true) {
  const rows = [],
    ids = new Set();
  let offset = 0,
    total;
  for (;;) {
    if (!isCurrent())
      throw new Error("Customer access changed; reload the inventory");
    const page = await readPage(offset);
    if (!isCurrent())
      throw new Error("Customer access changed; reload the inventory");
    if (
      !Array.isArray(page.items) ||
      !Number.isInteger(page.total) ||
      page.offset !== offset ||
      page.total < 0 ||
      (total !== undefined && total !== page.total)
    ) {
      throw new Error("Inventory changed during pagination; refresh to reload");
    }
    total = page.total;
    for (const row of page.items) {
      if (!row.id || ids.has(row.id))
        throw new Error(
          "Inventory changed during pagination; refresh to reload",
        );
      ids.add(row.id);
      rows.push(row);
    }
    offset += page.items.length;
    if (!page.has_more) {
      if (rows.length !== total)
        throw new Error("Incomplete inventory; refresh to reload");
      return rows;
    }
    if (!page.items.length || offset >= total)
      throw new Error("Invalid inventory pagination");
  }
}
