import { useI18n } from '../../i18n';
import { RUN_STATUS_TONE, sessionStatusLabel, solidTone } from './rightPanel/statusTone';
import type { SessionStatus } from '../../store/workspace';
import './codex-suite.css';

/** Every status the backend can report is listed, including the `unknown`
 *  placeholder, so the badge never has to invent a state. */
const DOT_PULSE: Record<SessionStatus, string> = {
  pending: '',
  idle: '',
  running: 'animate-pulse motion-reduce:animate-none',
  paused: '',
  completed: '',
  failed: '',
  stopped: '',
  unknown: '',
};

interface SessionStatusDotProps {
  status: SessionStatus;
  className?: string;
}

/**
 * The 6px tone dot every session surface shares. Its colour comes from the
 * inspector's tone palette rather than a second set of classes kept per file,
 * and the running pulse honours reduced motion.
 */
export function SessionStatusDot({ status, className = '' }: SessionStatusDotProps) {
  return (
    <span
      aria-hidden="true"
      className={`h-1.5 w-1.5 shrink-0 rounded-full ${solidTone(RUN_STATUS_TONE[status])} ${DOT_PULSE[status]} ${className}`}
    />
  );
}

interface SessionStatusBadgeProps {
  status: SessionStatus;
}

/**
 * The label comes from `right_panel.status.*`, the same keys the run summary and
 * the session sidebar read, so a status reads identically wherever it appears.
 * The badge uses the shared pill treatment for a compact status surface.
 */
export function SessionStatusBadge({ status }: SessionStatusBadgeProps) {
  const { t } = useI18n();
  const label = sessionStatusLabel(status, t);

  return (
    <span className="cx-pill" title={label}>
      <SessionStatusDot status={status} />
      {label}
    </span>
  );
}
