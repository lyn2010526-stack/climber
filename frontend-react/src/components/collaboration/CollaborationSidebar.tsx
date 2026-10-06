import { useState, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { useTranslation } from '../../i18n';
import { cn } from '../../lib/utils';

export interface SidebarSectionProps {
  title: string;
  /** Trailing summary such as a member count, taken from the backend response. */
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

/**
 * One collapsible block of the collaboration sidebar. Membership and topic are
 * collaboration context, so they render here next to the workspace instead of
 * as workspace sections.
 */
export function SidebarSection({ title, meta, actions, children }: SidebarSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const panelId = `collab-section-${title}`;

  return (
    <section className="min-w-0 border-b border-[var(--color-border-subtle)] last:border-b-0">
      <div className="flex items-center gap-1 py-2">
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={panelId}
          onClick={() => setExpanded(current => !current)}
          className="flex min-w-0 flex-1 items-center gap-1.5 rounded px-1 py-1 text-left text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
        >
          <ChevronDown
            size={12}
            aria-hidden
            className={cn('shrink-0 transition-transform', expanded ? '' : '-rotate-90')}
          />
          <span className="truncate">{title}</span>
          {meta !== undefined && meta !== null && (
            <span className="shrink-0 text-[var(--color-text-muted)]">{meta}</span>
          )}
        </button>
        {actions && <div className="flex shrink-0 items-center gap-1">{actions}</div>}
      </div>
      <div id={panelId} hidden={!expanded} className="min-w-0 pb-3">
        {children}
      </div>
    </section>
  );
}

export interface ParticipantListProps {
  members: Array<{ id: string; agent_id: string | null; role: string; status?: string }>;
  onRemove: (memberId: string) => void;
  removing: boolean;
  roleLabel: (role: string) => string;
  /** A failed or malformed response must never be presented as an empty roster. */
  error?: string;
  /** When set with `roles`, each row offers an inline role picker. */
  roles?: string[];
  onRoleChange?: (memberId: string, role: string) => void;
  roleChangeDisabled?: boolean;
}

/** Read-only membership list for the collaboration sidebar. */
export function ParticipantList({ members, onRemove, removing, roleLabel, error, roles, onRoleChange, roleChangeDisabled }: ParticipantListProps) {
  const { t } = useTranslation();
  if (error) return null;
  if (members.length === 0) {
    return <p className="px-1 py-2 text-xs text-[var(--color-text-muted)]">{t('collaboration.members.empty')}</p>;
  }
  return (
    <ul className="min-w-0 divide-y divide-[var(--color-border-subtle)]">
      {members.map(member => {
        const identity = member.agent_id || member.id;
        return (
          <li key={member.id} className="flex items-center gap-2 py-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs" title={identity}>{identity}</p>
              {roles && onRoleChange ? (
                <select
                  aria-label={t('collaboration.members.change_role', { defaultValue: 'Change role' })}
                  value={member.role}
                  disabled={roleChangeDisabled}
                  onChange={event => onRoleChange(member.id, event.target.value)}
                  className="mt-0.5 h-6 max-w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-1 text-[10px] text-[var(--color-text-muted)]"
                >
                  {!roles.includes(member.role) && <option value={member.role}>{roleLabel(member.role)}</option>}
                  {roles.map(value => <option key={value} value={value}>{roleLabel(value)}</option>)}
                </select>
              ) : (
                <p className="mt-0.5 truncate text-[10px] text-[var(--color-text-muted)]">
                  {roleLabel(member.role)}
                </p>
              )}
              <p className="mt-0.5 truncate text-[10px] text-[var(--color-text-muted)]">
                {member.status || t('collaboration.not_reported')}
              </p>
            </div>
            <button
              type="button"
              aria-label={t('collaboration.members.remove_named', { name: identity })}
              disabled={removing}
              onClick={() => onRemove(member.id)}
              className="shrink-0 rounded px-1.5 py-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-error)] disabled:opacity-50"
            >
              {t('common.remove')}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export interface AddMemberFormProps {
  submitting: boolean;
  agentId: string;
  role: string;
  agentIdPlaceholder: string;
  roleLabel: (role: string) => string;
  roles: string[];
  onAgentIdChange: (value: string) => void;
  onRoleChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
}

/** Inline member creation, rendered next to the participant list. */
export function AddMemberForm({
  submitting,
  agentId,
  role,
  agentIdPlaceholder,
  roleLabel,
  roles,
  onAgentIdChange,
  onRoleChange,
  onCancel,
  onSubmit,
}: AddMemberFormProps) {
  const { t } = useTranslation();
  return (
    <form
      className="mt-2 space-y-2 rounded-lg border border-[var(--color-border-subtle)] p-3"
      onSubmit={event => {
        event.preventDefault();
        if (submitting || !agentId.trim()) return;
        onSubmit();
      }}
    >
      <input
        aria-label={agentIdPlaceholder}
        placeholder={agentIdPlaceholder}
        value={agentId}
        onChange={event => onAgentIdChange(event.target.value)}
        className="w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-2 text-xs"
      />
      <select
        aria-label={t('collaboration.members.role')}
        value={role}
        onChange={event => onRoleChange(event.target.value)}
        className="w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-2 text-xs"
      >
        {roles.map(value => (
          <option key={value} value={value}>
            {roleLabel(value)}
          </option>
        ))}
      </select>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded px-2 py-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
        >
          {t('common.cancel')}
        </button>
        <button
          type="submit"
          disabled={submitting || !agentId.trim()}
          className="rounded bg-[var(--color-accent)] px-2 py-1 text-xs text-[var(--color-accent-text)] disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)]"
        >
          {submitting ? t('collaboration.members.adding') : t('common.add')}
        </button>
      </div>
    </form>
  );
}
