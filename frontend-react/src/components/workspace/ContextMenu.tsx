import { useEffect, useRef } from 'react';
import {
  Play, RotateCcw, Copy, Terminal, CheckCircle2,
  Trash2, Bookmark, Flag,
} from 'lucide-react';

interface ContextMenuItem {
  id: string;
  label: string;
  icon?: any;
  shortcut?: string;
  danger?: boolean;
  disabled?: boolean;
  action: () => void;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  // Adjust position to stay within viewport
  const adjustedY = Math.min(y, window.innerHeight - items.length * 36 - 20);

  return (
    <div
      ref={ref}
      className="fixed z-50 min-w-[180px] bg-[var(--color-bg-surface-primary)] border border-[var(--color-border-subtle)] rounded-lg shadow-xl py-1 overflow-hidden"
      style={{ left: x, top: adjustedY }}
    >
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => { item.action(); onClose(); }}
          disabled={item.disabled}
          className={`w-full flex items-center gap-2.5 px-3 py-1.5 text-xs transition-colors ${
            item.disabled
              ? 'text-[var(--color-text-muted)] cursor-not-allowed'
              : item.danger
                ? 'text-red-400 hover:bg-red-500/10'
                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-hover)]/50 hover:text-[var(--color-text-primary)]'
          }`}
        >
          {item.icon && <item.icon size={12} />}
          <span className="flex-1 text-left">{item.label}</span>
          {item.shortcut && (
            <kbd className="text-[10px] text-[var(--color-text-muted)]">{item.shortcut}</kbd>
          )}
        </button>
      ))}
    </div>
  );
}

// ─── Message Context Menu Items ────────────────────────────────────────────

export function getMessageContextMenu(_itemId: string, _itemType: string): ContextMenuItem[] {
  const base: ContextMenuItem[] = [
    { id: 'rerun', label: 'Re-run', icon: RotateCcw, action: () => {} },
    { id: 'view-json', label: 'View Raw JSON', icon: Terminal, action: () => {} },
    { id: 'copy-id', label: 'Copy ID', icon: Copy, action: () => {} },
    { id: 'copy-content', label: 'Copy Content', icon: Copy, action: () => {} },
    { id: 'breakpoint', label: 'Add Breakpoint', icon: Flag, action: () => {} },
  ];

  if (_itemType === 'tool-call') {
    base.push(
      { id: 'resume', label: 'Resume from Here', icon: Play, action: () => {} },
      { id: 'ignore', label: 'Ignore This Call', icon: CheckCircle2, action: () => {} },
    );
  }

  base.push(
    { id: 'save-memory', label: 'Save to Memory', icon: Bookmark, action: () => {} },
    { id: 'delete', label: 'Delete', icon: Trash2, danger: true, action: () => {} },
  );

  return base;
}
