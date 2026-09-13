import { Route, ScanSearch, Code2, ShieldCheck, ChartLine, PenLine, TerminalSquare, type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';
import { buildAgentVisualIdentity, paletteColor, type AgentIdentityInput, type AgentRole } from './agentVisualIdentity';

const ROLE_ICONS: Record<AgentRole, LucideIcon> = {
  plan: Route,
  research: ScanSearch,
  code: Code2,
  review: ShieldCheck,
  analysis: ChartLine,
  write: PenLine,
  ops: TerminalSquare,
};

export type AgentSigilSize = 36 | 44 | 56;

export interface AgentSigilProps extends AgentIdentityInput {
  size?: AgentSigilSize;
  className?: string;
}

const SIZE_CLASSES: Record<AgentSigilSize, string> = {
  36: 'h-9 w-9 rounded-[10px] text-xs',
  44: 'h-11 w-11 rounded-xl text-sm',
  56: 'h-14 w-14 rounded-[14px] text-base',
};

const ICON_PX: Record<AgentSigilSize, number> = {
  36: 16,
  44: 20,
  56: 26,
};

function withAlpha(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function AgentSigil({ id, name, provider, size = 44, className }: AgentSigilProps) {
  const identity = buildAgentVisualIdentity({ id, name, provider });
  const color = paletteColor(identity.hue);
  const RoleIcon = identity.role ? ROLE_ICONS[identity.role] : null;

  return (
    <div
      aria-hidden="true"
      data-sigil-hue={identity.hue}
      data-sigil-role={identity.role ?? 'initials'}
      className={cn(
        'relative flex shrink-0 items-center justify-center font-semibold',
        SIZE_CLASSES[size],
        className,
      )}
      style={{
        backgroundColor: withAlpha(color, 0.12),
        boxShadow: `inset 0 0 0 1px ${withAlpha(color, 0.35)}`,
        color,
      }}
    >
      {RoleIcon ? <RoleIcon size={ICON_PX[size]} strokeWidth={2} /> : (
        <span className="leading-none tracking-tight">{identity.initials}</span>
      )}
    </div>
  );
}

export default AgentSigil;
