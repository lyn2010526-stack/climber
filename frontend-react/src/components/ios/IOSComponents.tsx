import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import type { ReactNode, ReactElement } from 'react';

/* ─── iOS List Group (Settings-style) ─── */

interface IOSListItemProps {
  icon?: ReactElement;
  iconBg?: string;
  title: string;
  detail?: ReactNode;
  onClick?: () => void;
  showChevron?: boolean;
  danger?: boolean;
  className?: string;
}

export function IOSListItem({ icon, iconBg = 'var(--color-accent)', title, detail, onClick, showChevron = true, danger, className }: IOSListItemProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      className={cn(
        'ios-list-item w-full text-left',
        danger && 'active:!bg-[var(--color-error-subtle)]',
        className
      )}
      whileTap={{ backgroundColor: 'var(--color-bg-surface-2)' }}
      transition={{ duration: 0.1 }}
    >
      {icon && (
        <span className="ios-list-item-icon" style={{ background: iconBg }}>
          {icon}
        </span>
      )}
      <span className={cn('ios-list-item-title', danger && 'text-[var(--color-error)]')}>{title}</span>
      <span className="ios-list-item-detail">
        {detail}
        {showChevron && (
          <svg width="13" height="20" viewBox="0 0 13 20" fill="none" className="opacity-40 ml-1">
            <path d="M1 1L11 10L1 19" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
    </motion.button>
  );
}

interface IOSListGroupProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export function IOSListGroup({ title, children, className }: IOSListGroupProps) {
  return (
    <div className={className}>
      {title && (
        <p className="ios-footnote uppercase tracking-wide text-[var(--color-text-muted)] mb-2 px-4">
          {title}
        </p>
      )}
      <div className="ios-list-group">{children}</div>
    </div>
  );
}

/* ─── iOS Switch ─── */

interface IOSSwitchProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

export function IOSSwitch({ checked, onChange, disabled }: IOSSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      className={cn('ios-switch', checked && 'on', disabled && 'opacity-40 pointer-events-none')}
    >
      <span className="ios-switch-knob" />
    </button>
  );
}

/* ─── iOS Segmented Control ─── */

interface IOSSegmentOption {
  value: string;
  label: string;
}

interface IOSSegmentedControlProps {
  options: IOSSegmentOption[];
  value: string;
  onChange: (v: string) => void;
  className?: string;
}

export function IOSSegmentedControl({ options, value, onChange, className }: IOSSegmentedControlProps) {
  return (
    <div className={cn('ios-segmented', className)}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={cn('ios-segment', value === opt.value && 'active')}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* ─── iOS Card ─── */

interface IOSCardProps {
  children: ReactNode;
  elevated?: boolean;
  className?: string;
}

export function IOSCard({ children, elevated, className }: IOSCardProps) {
  return <div className={cn('ios-card', elevated && 'ios-card-elevated', className)}>{children}</div>;
}

/* ─── iOS Navbar ─── */

interface IOSNavbarProps {
  title: string;
  left?: ReactNode;
  right?: ReactNode;
  className?: string;
}

export function IOSNavbar({ title, left, right, className }: IOSNavbarProps) {
  return (
    <div className={cn('ios-navbar', className)}>
      <div className="w-20 flex justify-start">{left}</div>
      <span className="ios-navbar-title">{title}</span>
      <div className="w-20 flex justify-end">{right}</div>
    </div>
  );
}

/* ─── iOS Badge ─── */

interface IOSBadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

const badgeColors = {
  default: 'var(--color-bg-surface-3)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  info: 'var(--color-info)',
};

export function IOSBadge({ children, variant = 'default', className }: IOSBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center px-2 py-0.5 rounded-full text-white text-xs font-semibold min-w-[20px]',
        className
      )}
      style={{ background: badgeColors[variant] }}
    >
      {children}
    </span>
  );
}
