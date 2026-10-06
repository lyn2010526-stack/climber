import { useCallback, useMemo, useState } from 'react';

/**
 * Selection state for a sidebar's batch mode.
 *
 * Codex's `multi_select_picker` and cc-haha's `MCPServerMultiselectDialog` both
 * let the user toggle a list into a single batch, confirm once, and leave. The
 * Climber sidebar has no such mode yet, so this hook owns the "which rows are
 * ticked" bookkeeping while the toolbar stays presentational.
 *
 * The hook keeps ids in an array and derives everything from it, so a stale id
 * that disappears from the list is simply filtered out of the count instead of
 * needing a pruning effect.
 */

export interface SessionBatchItem {
  id: string;
  title: string;
}

export interface SessionBatchSelection {
  /** Selected ids that are still present in the list, in tick order. */
  selectedIds: string[];
  count: number;
  allSelected: boolean;
  /** At least one, but not all — drives the indeterminate select-all box. */
  someSelected: boolean;
  isSelected: (id: string) => boolean;
  toggle: (id: string) => void;
  toggleAll: (next: boolean) => void;
  clear: () => void;
}

export function useSessionBatchSelection(ids: readonly string[]): SessionBatchSelection {
  const [selected, setSelected] = useState<string[]>([]);

  const present = useMemo(() => new Set(ids), [ids]);
  const selectedIds = useMemo(() => selected.filter((id) => present.has(id)), [selected, present]);
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  const toggle = useCallback((id: string) => {
    setSelected((previous) =>
      previous.includes(id) ? previous.filter((value) => value !== id) : [...previous, id],
    );
  }, []);

  const toggleAll = useCallback(
    (next: boolean) => setSelected(next ? [...new Set(ids)] : []),
    [ids],
  );

  const clear = useCallback(() => setSelected([]), []);
  const isSelected = useCallback((id: string) => selectedSet.has(id), [selectedSet]);

  return {
    selectedIds,
    count: selectedIds.length,
    allSelected: ids.length > 0 && selectedIds.length === ids.length,
    someSelected: selectedIds.length > 0 && selectedIds.length < ids.length,
    isSelected,
    toggle,
    toggleAll,
    clear,
  };
}
