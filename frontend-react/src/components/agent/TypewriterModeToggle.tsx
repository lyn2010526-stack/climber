import { Type as TypeIcon, Zap } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { cycleTypewriterMode, isTypewriterActive, useTypewriterMode, type TypewriterMode } from './typewriterConfig';

const MODE_LABEL_KEY: Record<TypewriterMode, string> = {
  off: 'anchored.typewriter.mode_off',
  balanced: 'anchored.typewriter.mode_balanced',
  realtime: 'anchored.typewriter.mode_realtime',
  silky: 'anchored.typewriter.mode_silky',
};

/** Header control that cycles the assistant reveal preset (off / balanced / realtime / silky). */
export function TypewriterModeToggle() {
  const { t } = useI18n();
  const mode = useTypewriterMode();
  const active = isTypewriterActive(mode);
  const label = t(MODE_LABEL_KEY[mode]);
  return (
    <button
      type="button"
      data-testid="typewriter-mode-toggle"
      data-typewriter-mode={mode}
      aria-pressed={active}
      aria-label={t('anchored.typewriter.toggle_aria')}
      title={label}
      onClick={() => { cycleTypewriterMode(); }}
      className={cn(
        'flex shrink-0 items-center gap-[var(--space-1)] rounded-[var(--radius-pill)] border border-[var(--color-border-subtle)] px-2 py-px',
        'text-[11px] font-medium leading-[17px] transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
        active
          ? 'border-[var(--color-border-accent)] text-[var(--color-accent)]'
          : 'text-[var(--color-text-muted)] hover:border-[var(--color-border-default)] hover:text-[var(--color-text-secondary)]',
      )}
    >
      {active ? <Zap size={14} aria-hidden="true" /> : <TypeIcon size={14} aria-hidden="true" />}
      <span className="truncate">{label}</span>
    </button>
  );
}