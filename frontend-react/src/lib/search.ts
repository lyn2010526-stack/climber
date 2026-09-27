/**
 * Case-insensitive "does any of these fields contain the query" test, shared by
 * every catalog page (MCP servers, plugins, skills, agents). A blank query
 * matches everything, and a null/undefined field is treated as empty rather
 * than throwing, because catalog rows carry optional description/tags columns.
 */
export function includesQuery(values: (string | null | undefined)[], query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return values.some(value => (value ?? '').toLowerCase().includes(needle));
}
