import { AlertTriangle, CheckCircle2, CircleDashed, CircleSlash, Loader2, Pause } from 'lucide-react';
import type { Session } from '../../../store/workspace';
import { useI18n } from '../../../i18n';
import { cn } from '../../../lib/utils';
import { RUN_STATUS_TONE, sessionStatusLabel, textTone } from './statusTone';

/** One icon per canonical status; `unknown` reads as a question, not a state. */
const STATUS_ICONS = {
  pending: CircleDashed,
  idle: CircleSlash,
  running: Loader2,
  paused: Pause,
  completed: CheckCircle2,
  failed: AlertTriangle,
  stopped: CircleSlash,
  unknown: CircleDashed,
} as const;

/**
 * The run header states which run the inspector is looking at and nothing
 * more. Token and model figures live once in the overview group, so a reader
 * never sees the same number in two places.
 */
export function RunSummary({ session }: { session: Session | undefined }) {
  const { t } = useI18n();
  const tone = session ? textTone(RUN_STATUS_TONE[session.status]) : 'text-[var(--color-text-muted)]';
  const StatusIcon = session ? STATUS_ICONS[session.status] : null;

  return (
    <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] px-3 py-1.5">
      <span
        className="min-w-0 flex-1 truncate text-xs font-medium text-[var(--color-text-primary)]"
        title={session ? session.title || t('right_panel.summary.untitled') : undefined}
      >
        {session ? session.title || t('right_panel.summary.untitled') : t('right_panel.summary.no_session')}
      </span>
      {session && StatusIcon && (
        <span className={cn('flex shrink-0 items-center gap-1', tone)}>
          <StatusIcon size={11} className={cn(session.status === 'running' && 'animate-spin')} aria-hidden="true" />
          <span className="text-[11px] font-medium">{sessionStatusLabel(session.status, t)}</span>
        </span>
      )}
    </div>
  );
}
