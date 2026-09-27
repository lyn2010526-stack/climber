import { Cpu } from 'lucide-react';
import { useI18n } from '../../i18n';
import { RUN_STATUS_TONE, sessionStatusLabel, solidTone } from './rightPanel/statusTone';
import type { SessionStatus } from '../../store/workspace';

interface SessionStatusBadgeProps {
  status: SessionStatus;
}

/** Every status the backend can report is listed, including the `unknown`
 *  placeholder, so the badge never has to invent a state. */
const DOT_PULSE: Record<SessionStatus, string> = {
  pending: '',
  idle: '',
  running: 'animate-pulse',
  paused: '',
  completed: '',
  failed: '',
  stopped: '',
  unknown: '',
};

/**
 * The label comes from `right_panel.status.*`, the same keys the run summary and
 * the session sidebar read, so a status reads identically wherever it appears.
 * The dot colour comes from the inspector's tone palette rather than a second
 * set of CSS classes kept in this file.
 */
export function SessionStatusBadge({ status }: SessionStatusBadgeProps) {
  const { t } = useI18n();
  const label = sessionStatusLabel(status, t);

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-text-primary)]"
      title={label}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${solidTone(RUN_STATUS_TONE[status])} ${DOT_PULSE[status]}`} />
      <Cpu size={10} className="text-[var(--color-text-secondary)]" aria-hidden="true" />
      {label}
    </span>
  );
}
