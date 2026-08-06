import { Search, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface IOSSearchBarProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

export function IOSSearchBar({ value, onChange, placeholder = '搜索...', className }: IOSSearchBarProps) {
  return (
    <div className={cn('relative', className)}>
      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full h-10 pl-9 pr-9 rounded-[10px] bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] ios-body placeholder:text-[var(--color-text-muted)] outline-none focus:border-[var(--color-accent)] transition-colors"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

/* ─── iOS FAB (Floating Action Button) ─── */

interface IOSFabProps {
  icon: React.ReactNode;
  label?: string;
  onClick: () => void;
}

export function IOSFab({ icon, label, onClick }: IOSFabProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      className="fixed bottom-20 right-4 z-30 flex items-center gap-2 h-12 px-5 rounded-full bg-[var(--color-accent)] text-white shadow-lg shadow-[var(--color-accent-glow)] ios-spring active:scale-95"
      whileTap={{ scale: 0.92 }}
      transition={{ duration: 0.15 }}
    >
      {icon}
      {label && <span className="text-sm font-semibold">{label}</span>}
    </motion.button>
  );
}

/* ─── iOS Confirm Dialog ─── */

interface IOSConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  onConfirm: () => void;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

export function IOSConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  confirmText = '确认',
  cancelText = '取消',
  danger,
}: IOSConfirmDialogProps) {
  return (
    <motion.div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center p-4',
        !open && 'pointer-events-none'
      )}
      initial={false}
      animate={{ opacity: open ? 1 : 0 }}
      transition={{ duration: 0.15 }}
    >
      {open && (
        <>
          <div className="ios-backdrop absolute inset-0" onClick={() => onOpenChange(false)} />
          <motion.div
            className="relative w-full max-w-[270px] rounded-[14px] bg-[var(--color-bg-surface-1)]/95 backdrop-blur-xl border border-[var(--color-border-subtle)] overflow-hidden"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="px-4 pt-5 pb-3 text-center">
              <p className="ios-headline text-[var(--color-text-primary)]">{title}</p>
              {description && (
                <p className="ios-caption text-[var(--color-text-muted)] mt-1">{description}</p>
              )}
            </div>
            <div className="flex border-t border-[var(--color-border-subtle)]">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="flex-1 py-2.5 ios-body text-[var(--color-accent)] active:bg-[var(--color-bg-surface-2)] transition-colors"
              >
                {cancelText}
              </button>
              <button
                type="button"
                onClick={onConfirm}
                className={cn(
                  'flex-1 py-2.5 ios-body border-l border-[var(--color-border-subtle)] active:bg-[var(--color-bg-surface-2)] transition-colors',
                  danger ? 'text-[var(--color-error)] font-semibold' : 'text-[var(--color-accent)] font-semibold'
                )}
              >
                {confirmText}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </motion.div>
  );
}
