export default function InventoryPager({ data, onOffsetChange }) {
  if (!data) return null;
  const offset = data.offset || 0, limit = data.limit || 200, total = data.total || 0;
  const available = Math.max(0, Math.min(limit, total - offset));
  return <nav className="operational-actions" aria-label="Inventory pagination">
    <span>{available ? offset + 1 : 0}–{available ? offset + available : 0} of {total} records</span>
    <button disabled={!offset} onClick={() => onOffsetChange(Math.max(0, offset - limit))}>Previous page</button>
    <button disabled={!data.has_more} onClick={() => onOffsetChange(offset + limit)}>Next page</button>
  </nav>;
}
