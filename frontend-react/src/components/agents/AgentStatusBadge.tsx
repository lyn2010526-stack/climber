import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../i18n';

export interface AgentStatusFields {
  is_active?: boolean | null;
  model_id?: string | null;
  provider?: string | null;
}

/**
 * What the agents API actually tells us. The endpoint returns a model id and
 * a provider string; it never reports that credentials work, that the model
 * responds, or that a run is healthy. `unreported` therefore exists to say the
 * API sent no model fields at all, which is different from reporting them
 * blank.
 */
export type AgentStatus = 'configured' | 'incomplete' | 'disabled' | 'unreported';

export function resolveAgentStatus(agent: AgentStatusFields): AgentStatus {
  if (agent.is_active === false) return 'disabled';
  if (agent.model_id && agent.provider) return 'configured';
  // Null/undefined means the payload omitted the field; "" means the backend
  // reported the field and it is empty. Collapsing the two would claim a
  // misconfiguration the API never described.
  if (agent.model_id == null && agent.provider == null) return 'unreported';
  return 'incomplete';
}

const STATUS_CONFIG: Record<AgentStatus, { label: string; key: string; variant: 'success' | 'warning' | 'secondary'; dotClass: string; hintKey: string }> = {
  // Neutral, not success: a model id and provider are configuration the user
  // typed, not a verified working agent.
  configured: { label: 'Model configured', key: 'agents.status_model_configured', variant: 'secondary', dotClass: 'bg-[var(--color-text-muted)]', hintKey: 'agents.hint_model_configured' },
  incomplete: { label: 'Incomplete', key: 'agents.status_incomplete', variant: 'warning', dotClass: 'bg-[var(--color-warning)]', hintKey: 'agents.hint_incomplete' },
  disabled: { label: 'Disabled', key: 'agents.status_disabled', variant: 'secondary', dotClass: 'bg-[var(--color-text-muted)]', hintKey: 'agents.hint_disabled' },
  unreported: { label: 'Not reported', key: 'agents.status_unreported', variant: 'secondary', dotClass: 'bg-[var(--color-text-disabled)]', hintKey: 'agents.hint_unreported' },
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
      title={t(config.hintKey)}
      data-agent-status={status}
      className={cn('shrink-0', className)}
    >
      <span aria-hidden="true" className={cn('h-1.5 w-1.5 rounded-full', config.dotClass)} />
      {t(config.key)}
    </Badge>
  );
}

export default AgentStatusBadge;
