import React, { useState, useMemo, useCallback, useRef } from 'react';
import { cn } from '../../lib/utils';
import { ChevronRight, ChevronDown, Search, Folder, FolderOpen, FileText, GripVertical } from 'lucide-react';

export interface TreeNode {
  id: string;
  label: string;
  children?: TreeNode[];
  icon?: React.ReactNode;
  disabled?: boolean;
  metadata?: Record<string, unknown>;
}

export interface TreeViewProps {
  data: TreeNode[];
  selectable?: boolean;
  multiSelect?: boolean;
  selectedIds?: string[];
  onSelectionChange?: (ids: string[]) => void;
  expandable?: boolean;
  defaultExpandedIds?: string[];
  expandedIds?: string[];
  onExpandChange?: (ids: string[]) => void;
  searchable?: boolean;
  searchPlaceholder?: string;
  draggable?: boolean;
  onDragEnd?: (dragId: string, dropId: string) => void;
  onNodeClick?: (node: TreeNode) => void;
  onNodeDoubleClick?: (node: TreeNode) => void;
  className?: string;
  itemHeight?: number;
  indent?: number;
}

function TreeView({
  data,
  selectable = false,
  multiSelect = false,
  selectedIds = [],
  onSelectionChange,
  expandable = true,
  defaultExpandedIds,
  expandedIds,
  onExpandChange,
  searchable = false,
  searchPlaceholder = 'Search...',
  draggable = false,
  onDragEnd,
  onNodeClick,
  onNodeDoubleClick,
  className,
  itemHeight = 32,
  indent = 20,
}: TreeViewProps) {
  const [internalExpanded, setInternalExpanded] = useState<Set<string>>(new Set(defaultExpandedIds));
  const [searchQuery, setSearchQuery] = useState('');
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const dragNodeId = useRef<string | null>(null);

  const isControlled = expandedIds !== undefined;
  const expanded = isControlled ? new Set(expandedIds) : internalExpanded;

  const toggleExpand = useCallback((id: string) => {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    if (!isControlled) setInternalExpanded(next);
    onExpandChange?.(Array.from(next));
  }, [expanded, isControlled, onExpandChange]);

  const handleSelect = useCallback((id: string, e?: React.MouseEvent) => {
    if (!selectable || !onSelectionChange) return;
    if (multiSelect && (e?.ctrlKey || e?.metaKey)) {
      if (selectedIds.includes(id)) {
        onSelectionChange(selectedIds.filter(s => s !== id));
      } else {
        onSelectionChange([...selectedIds, id]);
      }
    } else {
      onSelectionChange([id]);
    }
  }, [selectable, multiSelect, onSelectionChange, selectedIds]);

  const matchesSearch = useCallback((node: TreeNode, query: string): boolean => {
    if (!query) return true;
    const lower = query.toLowerCase();
    if (node.label.toLowerCase().includes(lower)) return true;
    if (node.children) return node.children.some(child => matchesSearch(child, query));
    return false;
  }, []);

  const getMatchingIds = useCallback((nodes: TreeNode[], query: string): Set<string> => {
    const result = new Set<string>();
    nodes.forEach(node => {
      if (node.label.toLowerCase().includes(query.toLowerCase())) result.add(node.id);
      if (node.children) {
        const childMatches = getMatchingIds(node.children, query);
        childMatches.forEach(id => result.add(id));
        if (childMatches.size > 0) result.add(node.id);
      }
    });
    return result;
  }, []);

  const searchExpandedIds = useMemo(() => {
    if (!searchQuery) return null;
    return getMatchingIds(data, searchQuery);
  }, [searchQuery, data, getMatchingIds]);

  const flattened = useMemo(() => {
    const result: { node: TreeNode; depth: number }[] = [];
    const traverse = (nodes: TreeNode[], depth: number) => {
      nodes.forEach(node => {
        if (searchQuery && !matchesSearch(node, searchQuery)) return;
        result.push({ node, depth });
        if (node.children && (expanded.has(node.id) || searchExpandedIds?.has(node.id))) {
          traverse(node.children, depth + 1);
        }
      });
    };
    traverse(data, 0);
    return result;
  }, [data, expanded, searchQuery, matchesSearch, searchExpandedIds]);

  const handleDragStart = useCallback((e: React.DragEvent, id: string) => {
    dragNodeId.current = id;
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, id: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverId(id);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, dropId: string) => {
    e.preventDefault();
    const dragId = dragNodeId.current;
    if (dragId && dragId !== dropId && onDragEnd) {
      onDragEnd(dragId, dropId);
    }
    setDragOverId(null);
    dragNodeId.current = null;
  }, [onDragEnd]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent, node: TreeNode) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (selectable) handleSelect(node.id);
      onNodeClick?.(node);
    }
    if (e.key === 'ArrowRight' && node.children && !expanded.has(node.id)) {
      e.preventDefault();
      toggleExpand(node.id);
    }
    if (e.key === 'ArrowLeft' && node.children && expanded.has(node.id)) {
      e.preventDefault();
      toggleExpand(node.id);
    }
  }, [selectable, handleSelect, onNodeClick, expanded, toggleExpand]);

  return (
    <div className={cn('w-full border border-[var(--border-subtle)] rounded-xl bg-[var(--surface-bg)] overflow-hidden', className)}>
      {searchable && (
        <div className="p-3 border-b border-[var(--border-subtle)]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--border-default)] bg-[var(--surface-bg-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              aria-label="Search tree"
            />
          </div>
        </div>
      )}
      <div className="overflow-y-auto max-h-96" role="tree" aria-label="Tree view">
        {flattened.map(({ node, depth }) => {
          const isSelected = selectedIds.includes(node.id);
          const hasChildren = node.children && node.children.length > 0;
          const isExpanded = expanded.has(node.id) || searchExpandedIds?.has(node.id);

          return (
            <div
              key={node.id}
              role="treeitem"
              aria-selected={selectable ? isSelected : undefined}
              aria-expanded={hasChildren ? isExpanded : undefined}
              aria-level={depth + 1}
              tabIndex={0}
              style={{ height: itemHeight, paddingLeft: depth * indent + 8 }}
              className={cn(
                'flex items-center gap-1.5 px-2 cursor-pointer transition-colors select-none',
                isSelected ? 'bg-[var(--accent-subtle)]' : 'hover:bg-[var(--surface-bg-hover)]',
                node.disabled && 'opacity-50 cursor-not-allowed',
                dragOverId === node.id && 'bg-[var(--accent)]/10'
              )}
              onClick={(e) => {
                if (node.disabled) return;
                handleSelect(node.id, e);
                onNodeClick?.(node);
              }}
              onDoubleClick={() => onNodeDoubleClick?.(node)}
              onKeyDown={(e) => handleKeyDown(e, node)}
              draggable={draggable && !node.disabled}
              onDragStart={(e) => handleDragStart(e, node.id)}
              onDragOver={(e) => handleDragOver(e, node.id)}
              onDragLeave={() => setDragOverId(null)}
              onDrop={(e) => handleDrop(e, node.id)}
            >
              {draggable && (
                <GripVertical className="w-3.5 h-3.5 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 flex-shrink-0" />
              )}
              {expandable && hasChildren ? (
                <button
                  onClick={(e) => { e.stopPropagation(); toggleExpand(node.id); }}
                  className="p-0.5 rounded hover:bg-[var(--surface-bg-hover)] flex-shrink-0"
                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                  tabIndex={-1}
                >
                  <ChevronRight className={cn('w-3.5 h-3.5 text-[var(--text-muted)] transition-transform', isExpanded && 'rotate-90')} />
                </button>
              ) : (
                <span className="w-4.5 flex-shrink-0" />
              )}
              {node.icon || (hasChildren ? (
                isExpanded ? <FolderOpen className="w-4 h-4 text-[var(--accent)] flex-shrink-0" /> : <Folder className="w-4 h-4 text-[var(--accent)] flex-shrink-0" />
              ) : (
                <FileText className="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
              ))}
              <span className={cn('text-sm text-[var(--text-primary)] truncate', isSelected && 'font-medium')}>
                {node.label}
              </span>
            </div>
          );
        })}
        {flattened.length === 0 && (
          <div className="py-8 text-center text-sm text-[var(--text-muted)]">
            {searchQuery ? 'No matching items' : 'No items'}
          </div>
        )}
      </div>
    </div>
  );
}

export { TreeView };
