import { Brain, Gauge, Wrench } from 'lucide-react';
import type { Session } from '../../../../store/workspace';
import { useI18n } from '../../../../i18n';
import { KeyValueRow, SectionHeader } from '../PanelState';

/** A number the session actually reported. Absent stays absent in the panel. */
const isReported = (value: number | undefined): value is number =>
  typeof value === 'number' && Number.isFinite(value);

/**
 * The overview group is the single place where model configuration and token
 * budget are reported. Every row renders on every session, and a value the
 * backend never sent reads as "not reported" — a fabricated 0, 200000 or 0.7
 * would be indistinguishable from a real budget.
 */
export function ConfigSection({ session }: { session: Session | undefined }) {
  const { t } = useI18n();
  const notReported = t('right_panel.summary.not_reported');

  const modelConfig = session?.modelConfig;
  const provider = modelConfig?.provider;
  const modelId = modelConfig?.modelId;
  const temperature = modelConfig?.temperature;
  const maxTokens = modelConfig?.maxTokens;
  const skills = session?.activeSkills ?? [];
  const tools = session?.activeTools ?? [];
  const used = session?.tokenUsage?.used;
  const limit = session?.tokenUsage?.limit;
  const hasUsage = isReported(used) && used >= 0 && isReported(limit) && limit > 0;
  const percent = hasUsage ? Math.min(100, Math.round((used / limit) * 100)) : 0;

  return (
    <div className="space-y-3">
      <section>
        <SectionHeader title={t('right_panel.config.title')} />
        <div className="pt-1">
          <KeyValueRow label={t('right_panel.config.provider')} value={provider ?? notReported} />
          <KeyValueRow label={t('right_panel.config.model')} value={modelId ?? notReported} />
          <KeyValueRow
            label={t('right_panel.config.temperature')}
            value={isReported(temperature) ? temperature : notReported}
          />
          <KeyValueRow
            label={t('right_panel.config.max_tokens')}
            value={isReported(maxTokens) ? maxTokens : notReported}
          />
        </div>
      </section>

      <section>
        <SectionHeader title={t('right_panel.config.token_title')} />
        {hasUsage ? (
          <>
            <div className="flex items-baseline justify-between gap-3 pt-1">
              <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
                <Gauge size={12} aria-hidden="true" />
                {t('right_panel.summary.tokens')}
              </span>
              <span className="font-mono text-[11px] font-medium tabular-nums text-[var(--color-text-secondary)]">
                {t('right_panel.summary.token_of_limit', { used, limit })}
              </span>
            </div>
            <div
              className="mt-1.5 h-1 overflow-hidden rounded-full bg-[var(--color-bg-surface-3)]"
              role="progressbar"
              aria-label={t('right_panel.config.token_title')}
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full transition-[width] duration-300"
                style={{
                  width: `${percent}%`,
                  // Budget pressure is a status, so it is the only coloured element here.
                  backgroundColor:
                    percent >= 90
                      ? 'var(--color-error)'
                      : percent >= 75
                        ? 'var(--color-warning)'
                        : 'var(--color-info)',
                }}
              />
            </div>
          </>
        ) : (
          <p className="pt-1 text-[11px] text-[var(--color-text-muted)]">
            {t('right_panel.config.tokens_not_reported')}
          </p>
        )}
      </section>

      <section>
        <SectionHeader title={t('right_panel.config.skills_title')} count={skills.length} />
        {skills.length > 0 ? (
          <ul className="flex flex-wrap gap-1 pt-1">
            {skills.map((skill) => (
              <li
                key={skill}
                className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-text-secondary)]"
              >
                <Brain size={10} className="text-[var(--color-text-muted)]" aria-hidden="true" />
                {skill}
              </li>
            ))}
          </ul>
        ) : (
          <p className="pt-1 text-[11px] text-[var(--color-text-muted)]">{t('right_panel.config.no_skills')}</p>
        )}
      </section>

      <section>
        <SectionHeader title={t('right_panel.config.tools_title')} count={tools.length} />
        {tools.length > 0 ? (
          <ul className="flex flex-wrap gap-1 pt-1">
            {tools.map((tool) => (
              <li
                key={tool}
                className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-text-secondary)]"
              >
                <Wrench size={10} className="text-[var(--color-text-muted)]" aria-hidden="true" />
                {tool}
              </li>
            ))}
          </ul>
        ) : (
          <p className="pt-1 text-[11px] text-[var(--color-text-muted)]">{t('right_panel.config.no_tools')}</p>
        )}
      </section>
    </div>
  );
}
