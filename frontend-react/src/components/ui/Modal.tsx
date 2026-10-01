import React, { useEffect, useRef, useCallback, useId } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../i18n';
import { icons, iconSizes } from '../../lib/icons';
import { trapTab } from '../../lib/focusTrap';
import { Button } from './Button';

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
  fullscreen: 'max-w-full m-0 min-h-screen rounded-none',
};

/**
 * Where a dialog sits in the stack, which is the only thing the four states
 * vary. Each rung names how much of the host it suppresses, so the scrim depth
 * and the panel's own elevation move together:
 *
 * - `default` — a dialog over the page. Standard dim, panel on surface-1.
 * - `elevated` — a dialog over another dialog, so it takes the next surface
 *   rung, the stronger edge, and the deepest shadow to mark the stack.
 * - `overlay` — a dialog whose host must stay readable behind it, so the scrim
 *   lightens and the panel keeps the standard surface and edge.
 * - `backdrop` — a dialog that owns the screen while it is up, so the scrim
 *   closes up and the panel takes the deepest shadow on the standard surface.
 *
 * Shadow is spent on stack level and nothing else: no rung tints, glows or
 * blurs its own panel.
 */
export type ModalDepth = 'default' | 'elevated' | 'overlay' | 'backdrop';

interface ModalDepthSpec {
  /**
   * The scrim: the page token at a Tailwind opacity step, so the dim resolves
   * toward the theme's own base instead of introducing a second backdrop colour.
   * The step carries the whole dimming job, as the note on the table explains.
   */
  scrim: string;
  /** The panel fill, one or two steps off the page. */
  panel: string;
  /** The panel edge. */
  edge: string;
  /** The lift. */
  shadow: string;
  /** The action strip, always one rung below the panel so it stays visible. */
  footer: string;
}

/**
 * The scrim carries no frosted-glass filter, so alpha alone has to take the
 * legibility away from whatever sits behind the dialog. That is why every step
 * below runs higher than a blur-assisted scrim would need: the opacity does the
 * defocusing on its own, and the four rungs keep the order a viewer reads as a
 * stack.
 */
const MODAL_DEPTHS: Record<ModalDepth, ModalDepthSpec> = {
  default: {
    scrim: 'bg-[var(--color-bg-page)]/80',
    panel: 'bg-[var(--color-bg-surface-1)]',
    edge: 'border-[var(--color-border-default)]',
    shadow: 'shadow-[var(--shadow-lg)]',
    footer: 'bg-[var(--color-bg-surface-2)]',
  },
  elevated: {
    // A dialog stacked on another dialog dims by the same step as one over the
    // page: its host is already a dialog, so a second dim would only muddy the
    // panel edge. The stack is marked by the surface rung and the lift instead.
    scrim: 'bg-[var(--color-bg-page)]/80',
    panel: 'bg-[var(--color-bg-surface-2)]',
    edge: 'border-[var(--color-border-strong)]',
    shadow: 'shadow-[var(--shadow-xl)]',
    // A surface-2 footer on a surface-2 panel would read as no strip at all.
    footer: 'bg-[var(--color-bg-surface-3)]',
  },
  overlay: {
    // The host has to stay readable through this one, so it keeps the most of
    // the page showing and spends nothing on a surface rung or a stronger edge.
    scrim: 'bg-[var(--color-bg-page)]/55',
    panel: 'bg-[var(--color-bg-surface-1)]',
    edge: 'border-[var(--color-border-default)]',
    shadow: 'shadow-[var(--shadow-lg)]',
    footer: 'bg-[var(--color-bg-surface-2)]',
  },
  backdrop: {
    // Owning the screen means the host should be a memory rather than a page,
    // so this is the one rung that closes nearly all of it.
    scrim: 'bg-[var(--color-bg-page)]/92',
    panel: 'bg-[var(--color-bg-surface-1)]',
    edge: 'border-[var(--color-border-default)]',
    shadow: 'shadow-[var(--shadow-xl)]',
    footer: 'bg-[var(--color-bg-surface-2)]',
  },
};

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  className?: string;
  closeOnOverlay?: boolean;
  closeOnEsc?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'fullscreen';
  centered?: boolean;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  footer?: React.ReactNode;
  showClose?: boolean;
  depth?: ModalDepth;
}

/** Shared with the other dialog surfaces so the trap cannot drift per modal. */

const Modal = React.forwardRef<HTMLDivElement, ModalProps>(({
  open,
  onClose,
  children,
  className,
  closeOnOverlay = true,
  closeOnEsc = true,
  size = 'md',
  centered = true,
  title,
  description,
  icon,
  footer,
  showClose = true,
  depth = 'default',
}, ref) => {
  const { t } = useTranslation();
  const contentRef = useRef<HTMLDivElement>(null);
  const setContentRef = useCallback((node: HTMLDivElement | null) => {
    contentRef.current = node;
    if (typeof ref === 'function') return ref(node);
    if (ref) ref.current = node;
  }, [ref]);
  const generatedId = useId();
  const titleId = `${generatedId}-title`;
  const descId = `${generatedId}-desc`;
  const rung = MODAL_DEPTHS[depth];

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    const timer = window.setTimeout(() => contentRef.current?.focus(), 0);
    document.body.style.overflow = 'hidden';
    return () => {
      window.clearTimeout(timer);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [open]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && closeOnEsc) {
      onClose();
    }
    if (e.key === 'Tab' && contentRef.current) {
      if (trapTab(contentRef.current, e.shiftKey)) e.preventDefault();
    }
  }, [closeOnEsc, onClose]);

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, handleKeyDown]);

  if (!open) return null;

  return createPortal(
    <div
      className={cn(
        'fixed inset-0 z-[var(--z-modal)] flex p-[var(--space-4)]',
        centered ? 'items-center justify-center' : 'items-start justify-center pt-[var(--space-16)]'
      )}
    >
      {/* The scrim is the page colour at a rung-specific alpha. There is no
          glass filter behind it, so the alpha is what pushes the host out of
          focus, and it is held high enough that text behind the dialog stops
          competing with it. It carries no hue of its own, which keeps the
          dialog the only saturated thing here. */}
      <div
        data-modal-overlay=""
        data-state="open"
        data-depth={depth}
        className={cn('absolute inset-0 animate-fadeIn motion-reduce:animate-none', rung.scrim)}
        onClick={closeOnOverlay ? onClose : undefined}
        aria-hidden="true"
      />
      {/* role="dialog" belongs on the element that owns the content, not on
          the overlay wrapper, so assistive tech scopes the label and the
          focus trap to the panel itself. */}
      <div
        ref={setContentRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descId : undefined}
        data-depth={depth}
        tabIndex={-1}
        className={cn(
          'relative w-full border',
          rung.panel,
          rung.edge,
          // The iOS corner rung (20px) reads softer than the generic xl rung at
          // dialog scale, and the spring entrance lives in the token layer as
          // `.modal-panel-in` — the scrim stays alpha-only by contract.
          'rounded-[var(--radius-ios-lg)] max-h-[90vh] overflow-hidden flex flex-col modal-panel-in',
          rung.shadow,
          'focus-visible:outline-none',
          sizeClasses[size],
          className
        )}
      >
        {showClose && (
          <button type="button"
            onClick={onClose}
            className={cn(
              'absolute top-[var(--space-3)] right-[var(--space-3)] z-10 rounded-[var(--radius-lg)] p-[var(--space-2)]',
              'text-[var(--color-text-muted)] transition-colors motion-reduce:transition-none',
              'hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
              'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]'
            )}
            aria-label={t('common.close_dialog')}
          >
            <icons.close size={iconSizes.md} aria-hidden="true" focusable="false" />
          </button>
        )}
        {(title || description || icon) && (
          <div className={cn('border-b border-[var(--color-border-subtle)] px-[var(--space-6)] pt-[var(--space-6)] pb-[var(--space-4)]', showClose && 'pr-[var(--space-12)]')}>
            {icon && <div className="mb-[var(--space-2)] text-[var(--color-text-secondary)] [&>svg]:size-[var(--icon-lg)]">{icon}</div>}
            {title && (
              <h2 id={titleId} className="text-[var(--text-base)] font-semibold text-[var(--color-text-primary)]">
                {title}
              </h2>
            )}
            {description && (
              <p id={descId} className="mt-[var(--space-1)] text-[var(--text-sm)] text-[var(--color-text-muted)]">
                {description}
              </p>
            )}
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-[var(--space-6)]">
          {children}
        </div>
        {footer && (
          <div className={cn('border-t border-[var(--color-border-subtle)] px-[var(--space-6)] py-[var(--space-4)]', rung.footer)}>
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
});
Modal.displayName = 'Modal';

export interface ConfirmDialogProps extends Omit<ModalProps, 'children' | 'footer'> {
  onConfirm: () => void;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  loading?: boolean;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  onConfirm,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'info',
  loading = false,
  onClose,
  ...props
}) => {
  return (
    <Modal
      {...props}
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-[var(--space-2)]">
          <Button type="button"
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            {cancelText}
          </Button>
          {/* One destructive style for every destructive outcome. `warning`
              shares it so a confirm that destroys data always looks like it. */}
          <Button type="button"
            variant={variant === 'info' ? 'primary' : 'destructive'}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmText}
          </Button>
        </div>
      }
    />
  );
};

/**
 * The three sub-panels, for callers that compose a dialog body themselves.
 * They render the standard depth recipe, because a caller assembling its own
 * layout is also choosing its own surface rungs; the `depth` prop drives the
 * strip only when the `footer` prop is used.
 */
const ModalHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('border-b border-[var(--color-border-subtle)] px-[var(--space-6)] pt-[var(--space-6)] pb-[var(--space-4)]', className)} {...props} />
  )
);
ModalHeader.displayName = 'ModalHeader';

const ModalBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex-1 overflow-y-auto px-[var(--space-6)] pb-[var(--space-6)]', className)} {...props} />
  )
);
ModalBody.displayName = 'ModalBody';

const ModalFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center justify-end gap-[var(--space-2)] border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-[var(--space-6)] py-[var(--space-4)]', className)} {...props} />
  )
);
ModalFooter.displayName = 'ModalFooter';

export { Modal, ConfirmDialog, ModalHeader, ModalBody, ModalFooter, MODAL_DEPTHS };
