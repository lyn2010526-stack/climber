import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

interface NavGroupProps {
  label: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function NavGroup({ label, icon, defaultOpen = false, children, className }: NavGroupProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={cn('mb-1', className)}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold uppercase tracking-wider transition-colors duration-200"
        style={{ color: 'var(--color-text-muted)' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = 'var(--color-text-secondary)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = 'var(--color-text-muted)';
        }}
      >
        {icon && <span className="opacity-70">{icon}</span>}
        <span className="flex-1 text-left">{label}</span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      <div
        className="overflow-hidden transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
        style={{
          maxHeight: open ? '500px' : '0px',
          opacity: open ? 1 : 0,
        }}
      >
        <div className="space-y-0.5 pt-0.5 pb-1">
          {children}
        </div>
      </div>
    </div>
  );
}
