/**
 * Toggle membership of a single id in an immutable list, preserving order.
 *
 * Selection lists across the app (agent tools, agent skills, factory-mode
 * skills) are all the same "add when absent, drop when present" update, so the
 * one implementation lives here.
 */
export function toggleListItem(items: readonly string[], id: string): string[] {
  return items.includes(id) ? items.filter(item => item !== id) : [...items, id];
}
