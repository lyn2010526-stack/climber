import React, { useState, useMemo, useCallback } from 'react';
import { cn } from '../../lib/utils';
import { ChevronUp, ChevronDown, ChevronsUpDown, Loader2 } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  width?: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (row: T, index: number) => React.ReactNode;
  className?: string;
}

export interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  sortable?: boolean;
  selectable?: boolean;
  selectedRows?: string[];
  onSelectionChange?: (selected: string[]) => void;
  expandable?: boolean;
  renderExpanded?: (row: T) => React.ReactNode;
  loading?: boolean;
  emptyMessage?: string;
  stickyHeader?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
  className?: string;
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string;
}

function Table<T extends Record<string, unknown>>({
  columns,
  data,
  keyExtractor,
  sortable = false,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  expandable = false,
  renderExpanded,
  loading = false,
  emptyMessage = 'No data available',
  stickyHeader = false,
  pagination,
  className,
  onRowClick,
  rowClassName,
}: TableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const handleSort = useCallback((key: string) => {
    if (!sortable) return;
    setSortConfig(prev => {
      if (prev?.key === key) {
        if (prev.direction === 'asc') return { key, direction: 'desc' };
        return null;
      }
      return { key, direction: 'asc' };
    });
  }, [sortable]);

  const handleSelectAll = useCallback((checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange(data.map(keyExtractor));
    } else {
      onSelectionChange([]);
    }
  }, [data, keyExtractor, onSelectionChange]);

  const handleSelectRow = useCallback((key: string, checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange([...selectedRows, key]);
    } else {
      onSelectionChange(selectedRows.filter(k => k !== key));
    }
  }, [selectedRows, onSelectionChange]);

  const toggleExpand = useCallback((key: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const sortedData = useMemo(() => {
    if (!sortConfig) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortConfig]);

  const allSelected = data.length > 0 && selectedRows.length === data.length;
  const someSelected = selectedRows.length > 0 && selectedRows.length < data.length;

  const renderSortIcon = (column: Column<T>) => {
    if (!column.sortable && !sortable) return null;
    const isActive = sortConfig?.key === column.key;
    if (!isActive) return <ChevronsUpDown className="w-[var(--icon-xs)] h-[var(--icon-xs)] text-[var(--text-muted)]" />;
    if (sortConfig.direction === 'asc') return <ChevronUp className="w-[var(--icon-xs)] h-[var(--icon-xs)] text-[var(--accent)]" />;
    return <ChevronDown className="w-[var(--icon-xs)] h-[var(--icon-xs)] text-[var(--accent)]" />;
  };

  return (
    <div className={cn('w-full overflow-hidden border border-[var(--border-subtle)] rounded-[var(--radius-xl)] bg-[var(--surface-bg)]', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-[var(--font-size-sm)]" role="grid">
          <thead className={cn('bg-[var(--surface-bg-subtle)] border-b border-[var(--border-subtle)]', stickyHeader && 'sticky top-0 z-10')}>
            <tr>
              {selectable && (
                <th className="w-10 px-[var(--space-3)] py-[var(--space-3)]">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected; }}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="w-[var(--icon-sm)] h-[var(--icon-sm)] rounded-[var(--radius-sm)] border-[var(--border-default)] text-[var(--accent)] focus:ring-[var(--focus-ring-color)] cursor-pointer"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {expandable && <th className="w-10 px-[var(--space-3)] py-[var(--space-3)]" />}
              {columns.map(col => (
                <th
                  key={col.key}
                  className={cn(
                    'px-[var(--space-3)] py-[var(--space-3)] text-left font-medium text-[var(--text-secondary)] whitespace-nowrap',
                    (col.sortable || sortable) && 'cursor-pointer select-none hover:text-[var(--text-primary)]',
                    col.className
                  )}
                  style={{ width: col.width }}
                  onClick={() => handleSort(col.key)}
                  aria-sort={sortConfig?.key === col.key ? (sortConfig.direction === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  <div className="flex items-center gap-[var(--space-1)]">
                    {col.header}
                    {renderSortIcon(col)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {loading ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0) + (expandable ? 1 : 0)} className="py-[var(--space-12)] text-center">
                  <div className="flex flex-col items-center gap-[var(--space-3)]">
                    <Loader2 className="w-[var(--icon-xl)] h-[var(--icon-xl)] text-[var(--accent)] animate-spin" />
                    <span className="text-[var(--text-muted)]">Loading...</span>
                  </div>
                </td>
              </tr>
            ) : sortedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0) + (expandable ? 1 : 0)} className="py-[var(--space-12)] text-center">
                  <span className="text-[var(--text-muted)]">{emptyMessage}</span>
                </td>
              </tr>
            ) : (
              sortedData.map((row, rowIndex) => {
                const rowKey = keyExtractor(row);
                const isSelected = selectedRows.includes(rowKey);
                const isExpanded = expandedRows.has(rowKey);

                return (
                  <React.Fragment key={rowKey}>
                    <tr
                      className={cn(
                        'transition-colors duration-[var(--transition-fast)]',
                        isSelected ? 'bg-[var(--accent-subtle)]' : 'hover:bg-[var(--surface-bg-hover)]',
                        onRowClick && 'cursor-pointer',
                        rowClassName?.(row)
                      )}
                      onClick={() => onRowClick?.(row)}
                      aria-selected={selectable ? isSelected : undefined}
                    >
                      {selectable && (
                        <td className="px-[var(--space-3)] py-[var(--space-3)]">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => handleSelectRow(rowKey, e.target.checked)}
                            className="w-[var(--icon-sm)] h-[var(--icon-sm)] rounded-[var(--radius-sm)] border-[var(--border-default)] text-[var(--accent)] focus:ring-[var(--focus-ring-color)] cursor-pointer"
                            aria-label={`Select row ${rowIndex + 1}`}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
                      )}
                      {expandable && (
                        <td className="px-[var(--space-3)] py-[var(--space-3)]">
                          <button
                            onClick={(e) => { e.stopPropagation(); toggleExpand(rowKey); }}
                            className="p-[var(--space-0-5)] rounded-[var(--radius-sm)] hover:bg-[var(--surface-bg-hover)] text-[var(--text-muted)]"
                            aria-expanded={isExpanded}
                            aria-label={isExpanded ? 'Collapse row' : 'Expand row'}
                          >
                            <ChevronDown className={cn('w-[var(--icon-sm)] h-[var(--icon-sm)] transition-transform', isExpanded && 'rotate-180')} />
                          </button>
                        </td>
                      )}
                      {columns.map(col => (
                        <td key={col.key} className={cn('px-[var(--space-3)] py-[var(--space-3)] text-[var(--text-primary)]', col.className)}>
                          {col.render ? col.render(row, rowIndex) : String(row[col.key] ?? '')}
                        </td>
                      ))}
                    </tr>
                    {expandable && isExpanded && renderExpanded && (
                      <tr>
                        <td colSpan={columns.length + (selectable ? 1 : 0) + 1} className="px-[var(--space-4)] py-[var(--space-4)] bg-[var(--surface-bg-subtle)]">
                          {renderExpanded(row)}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="flex items-center justify-between px-[var(--space-4)] py-[var(--space-3)] border-t border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)]">
          <span className="text-[var(--font-size-xs)] text-[var(--text-muted)]">
            {(pagination.page - 1) * pagination.pageSize + 1}-{Math.min(pagination.page * pagination.pageSize, pagination.total)} of {pagination.total}
          </span>
          <div className="flex items-center gap-[var(--space-1)]">
            <button
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className={cn(
                'h-[var(--size-sm)] px-[var(--space-2-5)] text-[var(--font-size-xs)] font-medium rounded-[var(--radius-md)]',
                'border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)]',
                'hover:bg-[var(--surface-bg-hover)] transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              Previous
            </button>
            <span className="px-[var(--space-2)] text-[var(--font-size-xs)] text-[var(--text-secondary)]">
              {pagination.page} / {Math.ceil(pagination.total / pagination.pageSize)}
            </span>
            <button
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page >= Math.ceil(pagination.total / pagination.pageSize)}
              className={cn(
                'h-[var(--size-sm)] px-[var(--space-2-5)] text-[var(--font-size-xs)] font-medium rounded-[var(--radius-md)]',
                'border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)]',
                'hover:bg-[var(--surface-bg-hover)] transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <thead ref={ref} className={cn('bg-[var(--surface-bg-subtle)] border-b border-[var(--border-subtle)]', className)} {...props} />
  )
);
TableHeader.displayName = 'TableHeader';

const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn('divide-y divide-[var(--border-subtle)]', className)} {...props} />
  )
);
TableBody.displayName = 'TableBody';

const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr ref={ref} className={cn('transition-colors hover:bg-[var(--surface-bg-hover)]', className)} {...props} />
  )
);
TableRow.displayName = 'TableRow';

const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn('px-[var(--space-3)] py-[var(--space-3)] text-[var(--font-size-sm)] text-[var(--text-primary)]', className)} {...props} />
  )
);
TableCell.displayName = 'TableCell';

export { Table, TableHeader, TableBody, TableRow, TableCell };
