import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../i18n';

export interface AgentStatusFields {
  is_active?: boolean | null;
  model_id?: string | null;
  provider?: string | null;
}

export type AgentStatus = 'configured' | 'incomplete' | 'disabled';

export function resolveAgentStatus(agent: AgentStatusFields): AgentStatus {
  if (agent.is_active === false) return 'disabled';
  if (agent.model_id && agent.provider) return 'configured';
  return 'incomplete';
}

const STATUS_CONFIG: Record<AgentStatus, { label: string; key: string; variant: 'success' | 'warning' | 'secondary'; dotClass: string }> = {
  configured: { label: 'Configured', key: 'agents.status_configured', variant: 'success', dotClass: 'bg-[var(--color-success)]' },
  incomplete: { label: 'Incomplete', key: 'agents.status_incomplete', variant: 'warning', dotClass: 'bg-[var(--color-warning)]' },
  disabled: { label: 'Disabled', key: 'agents.status_disabled', variant: 'secondary', dotClass: 'bg-[var(--color-text-muted)]' },
};

export interface AgentStatusBadgeProps {
  agent: AgentStatusFields;
  className?: string;
}

export function AgentStatusBadge({ agent, className }: AgentStatusBadgeProps) {
  const { t } = useTranslation();
  const status = resolveAgentStatus(agent);
  const config = STATUS_CONFIG[status];
  return (
    <Badge
      variant={config.variant}
      size="xs"
      role="status"
      aria-label={t(config.key)}
      data-agent-status={status}
      className={cn('shrink-0', className)}
    >
      <span aria-hidden="true" className={cn('h-1.5 w-1.5 rounded-full', config.dotClass)} />
      {config.label}
    </Badge>
  );
}

export default AgentStatusBadge;
