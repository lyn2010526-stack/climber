import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import type { SlashCommandInfo } from './slashCommands';
import { inlineSlashCompletion } from './slashInline';

/**
 * Draws the ghost completion produced by `slashInline`. Purely presentational:
 * it is `aria-hidden` so the dropdown stays the single accessible listbox, and
 * positioning is the caller's job — the composer anchors it over the textarea.
 */
export interface SlashInlineCompletionProps {
  input: string;
  catalog: SlashCommandInfo[];
  isStreaming?: boolean;
  className?: string;
  style?: CSSProperties;
}

export function SlashInlineCompletion({
  input,
  catalog,
  isStreaming = false,
  className,
  style,
}: SlashInlineCompletionProps) {
  const { t } = useI18n();
  const completion = useMemo(
    () => inlineSlashCompletion(input, catalog, isStreaming),
    [input, catalog, isStreaming],
  );

  if (!completion) return null;

  return (
    <span
      aria-hidden="true"
      data-testid="slash-inline-completion"
      data-command={completion.command.name}
      style={style}
      className={cn(
        'pointer-events-none select-none whitespace-pre text-[length:var(--text-sm)] leading-relaxed',
        className,
      )}
    >
      {/* The typed prefix is laid out but hidden, which is what puts the ghost
          text at the caret rather than at the start of the field. */}
      <span className="invisible">{completion.typed}</span>
      <span className="text-[var(--color-text-muted)]">{completion.suffix}</span>
      <span className="ms-[var(--space-2)] align-middle font-mono text-[length:var(--text-2xs)] text-[var(--color-text-disabled)]">
        {t('slash.inline_accept_hint', { defaultValue: 'Tab 补全' })}
      </span>
    </span>
  );
}

export default SlashInlineCompletion;
