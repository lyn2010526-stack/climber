import React, { useState, useMemo, useCallback } from 'react';
import { cn } from '../../lib/utils';
import { ChevronUp, ChevronDown, ChevronsUpDown, Search, Loader2, Trash2, Download } from 'lucide-react';

export interface DataTableColumn<T> {
  key: string;
  header: string;
  width?: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (row: T, index: number) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  sortable?: boolean;
  filterable?: boolean;
  selectable?: boolean;
  selectedRows?: string[];
  onSelectionChange?: (selected: string[]) => void;
  batchActions?: { label: string; icon?: React.ReactNode; onClick: (selected: string[]) => void; variant?: 'default' | 'destructive' }[];
  loading?: boolean;
  emptyMessage?: string;
  stickyHeader?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    pageSizeOptions?: number[];
    onPageSizeChange?: (size: number) => void;
  };
  className?: string;
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string;
  searchPlaceholder?: string;
  darkMode?: boolean;
}

function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyExtractor,
  sortable = true,
  filterable = false,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  batchActions,
  loading = false,
  emptyMessage = 'No data available',
  stickyHeader = false,
  pagination,
  className,
  onRowClick,
  rowClassName,
  searchPlaceholder = 'Search...',
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});

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

  const filteredData = useMemo(() => {
    let result = data;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(row =>
        columns.some(col => {
          const val = row[col.key];
          return val != null && String(val).toLowerCase().includes(query);
        })
      );
    }
    if (filterable) {
      Object.entries(filterValues).forEach(([key, value]) => {
        if (value) {
          const query = value.toLowerCase();
          result = result.filter(row => {
            const val = row[key];
            return val != null && String(val).toLowerCase().includes(query);
          });
        }
      });
    }
    return result;
  }, [data, searchQuery, filterValues, columns, filterable]);

  const handleSelectAll = useCallback((checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange(filteredData.map(keyExtractor));
    } else {
      onSelectionChange([]);
    }
  }, [filteredData, keyExtractor, onSelectionChange]);

  const handleSelectRow = useCallback((key: string, checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange([...selectedRows, key]);
    } else {
      onSelectionChange(selectedRows.filter(k => k !== key));
    }
  }, [selectedRows, onSelectionChange]);

  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortConfig]);

  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    const start = (pagination.page - 1) * pagination.pageSize;
    return sortedData.slice(start, start + pagination.pageSize);
  }, [sortedData, pagination]);

  const allSelected = filteredData.length > 0 && selectedRows.length === filteredData.length && filteredData.every(row => selectedRows.includes(keyExtractor(row)));
  const someSelected = selectedRows.length > 0 && !allSelected;

  const renderSortIcon = (column: DataTableColumn<T>) => {
    if (!column.sortable && !sortable) return null;
    const isActive = sortConfig?.key === column.key;
    if (!isActive) return <ChevronsUpDown className="w-3.5 h-3.5 text-[var(--text-muted)]" />;
    if (sortConfig.direction === 'asc') return <ChevronUp className="w-3.5 h-3.5 text-[var(--accent)]" />;
    return <ChevronDown className="w-3.5 h-3.5 text-[var(--accent)]" />;
  };

  const totalPages = pagination ? Math.ceil(sortedData.length / pagination.pageSize) : 1;

  return (
    <div className={cn('w-full overflow-hidden border border-[var(--border-subtle)] rounded-xl bg-[var(--surface-bg)]', className)}>
      {(filterable || (selectable && selectedRows.length > 0)) && (
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)]">
          {filterable && (
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                aria-label="Search table"
              />
            </div>
          )}
          {selectable && selectedRows.length > 0 && (
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-xs text-[var(--text-secondary)]">{selectedRows.length} selected</span>
              {batchActions?.map((action, i) => (
                <button
                  key={i}
                  onClick={() => action.onClick(selectedRows)}
                  className={cn(
                    'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors',
                    action.variant === 'destructive'
                      ? 'border-red-500/30 text-red-400 hover:bg-red-500/10'
                      : 'border-[var(--border-default)] text-[var(--text-primary)] hover:bg-[var(--surface-bg-hover)]'
                  )}
                >
                  {action.icon}
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="grid" aria-label="Data table">
          <thead className={cn('bg-[var(--surface-bg-subtle)] border-b border-[var(--border-subtle)]', stickyHeader && 'sticky top-0 z-10')}>
            <tr>
              {selectable && (
                <th className="w-10 px-3 py-3">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected; }}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="w-4 h-4 rounded border-[var(--border-default)] text-[var(--accent)] focus:ring-[var(--accent)] cursor-pointer"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {columns.map(col => (
                <th
                  key={col.key}
                  className={cn(
                    'px-3 py-3 text-left font-medium text-[var(--text-secondary)] whitespace-nowrap',
                    (col.sortable || sortable) && 'cursor-pointer select-none hover:text-[var(--text-primary)]',
                    col.className
                  )}
                  style={{ width: col.width }}
                  onClick={() => handleSort(col.key)}
                  aria-sort={sortConfig?.key === col.key ? (sortConfig.direction === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  <div className="flex items-center gap-1">
                    {col.header}
                    {renderSortIcon(col)}
                  </div>
                  {filterable && col.filterable && (
                    <input
                      type="text"
                      value={filterValues[col.key] || ''}
                      onChange={(e) => setFilterValues(prev => ({ ...prev, [col.key]: e.target.value }))}
                      onClick={(e) => e.stopPropagation()}
                      placeholder={`Filter ${col.header.toLowerCase()}...`}
                      className="mt-1.5 w-full px-2 py-1 text-xs rounded border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                      aria-label={`Filter by ${col.header}`}
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {loading ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} className="py-12 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-6 h-6 text-[var(--accent)] animate-spin" />
                    <span className="text-[var(--text-muted)]">Loading...</span>
                  </div>
                </td>
              </tr>
            ) : paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} className="py-12 text-center">
                  <span className="text-[var(--text-muted)]">{emptyMessage}</span>
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIndex) => {
                const rowKey = keyExtractor(row);
                const isSelected = selectedRows.includes(rowKey);
                return (
                  <tr
                    key={rowKey}
                    className={cn(
                      'transition-colors duration-150',
                      isSelected ? 'bg-[var(--accent-subtle)]' : 'hover:bg-[var(--surface-bg-hover)]',
                      onRowClick && 'cursor-pointer',
                      rowClassName?.(row)
                    )}
                    onClick={() => onRowClick?.(row)}
                    aria-selected={selectable ? isSelected : undefined}
                  >
                    {selectable && (
                      <td className="px-3 py-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => handleSelectRow(rowKey, e.target.checked)}
                          className="w-4 h-4 rounded border-[var(--border-default)] text-[var(--accent)] focus:ring-[var(--accent)] cursor-pointer"
                          aria-label={`Select row ${rowIndex + 1}`}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                    )}
                    {columns.map(col => (
                      <td key={col.key} className={cn('px-3 py-3 text-[var(--text-primary)]', col.className)}>
                        {col.render ? col.render(row, rowIndex) : String(row[col.key] ?? '')}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)]" role="navigation" aria-label="Pagination">
          <div className="flex items-center gap-3">
            <span className="text-xs text-[var(--text-muted)]">
              {((pagination.page - 1) * pagination.pageSize) + 1}-{Math.min(pagination.page * pagination.pageSize, sortedData.length)} of {sortedData.length}
            </span>
            {pagination.pageSizeOptions && pagination.onPageSizeChange && (
              <select
                value={pagination.pageSize}
                onChange={(e) => pagination.onPageSizeChange!(Number(e.target.value))}
                className="text-xs border border-[var(--border-default)] rounded-md px-2 py-1 bg-[var(--surface-bg)] text-[var(--text-primary)]"
                aria-label="Items per page"
              >
                {pagination.pageSizeOptions.map(size => (
                  <option key={size} value={size}>{size} / page</option>
                ))}
              </select>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="h-8 px-3 text-xs font-medium rounded-lg border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)] hover:bg-[var(--surface-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (pagination.page <= 3) {
                pageNum = i + 1;
              } else if (pagination.page >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = pagination.page - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => pagination.onPageChange(pageNum)}
                  className={cn(
                    'h-8 w-8 text-xs font-medium rounded-lg transition-colors',
                    pagination.page === pageNum
                      ? 'bg-[var(--accent)] text-white'
                      : 'border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)] hover:bg-[var(--surface-bg-hover)]'
                  )}
                  aria-label={`Page ${pageNum}`}
                  aria-current={pagination.page === pageNum ? 'page' : undefined}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page >= totalPages}
              className="h-8 px-3 text-xs font-medium rounded-lg border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)] hover:bg-[var(--surface-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export { DataTable };
