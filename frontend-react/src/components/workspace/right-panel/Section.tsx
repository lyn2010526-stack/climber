import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-[var(--color-bg-surface-2)] border border-[var(--color-border-default)] rounded-2xl overflow-hidden backdrop-blur-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        <div className="p-1 rounded-lg bg-[var(--color-accent-subtle)] text-[var(--color-accent)]">
          <Icon size={11} />
        </div>
        <span className="flex-1 text-left">{title}</span>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {expanded && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}
