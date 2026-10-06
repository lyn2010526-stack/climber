import { useCallback, useEffect, useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { api } from '../../api';
import { useI18n } from '../../i18n';
import { Button } from '../ui/Button';

/**
 * Full reasoning trace (GET /reason/{traceId}) plus its feedback thread
 * (GET /reason/{traceId}/feedback) and a thumbs up/down control
 * (POST /reason/{traceId}/feedback). Mounted from the reasoning-history
 * detail view when the row carries a trace id.
 */
export function ReasoningTraceDetail({ traceId }: { traceId: string }) {
  const { t } = useI18n();
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null);
  const [feedback, setFeedback] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<'up' | 'down' | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [traceData, feedbackData] = await Promise.all([
        api.getReasoningTrace(traceId),
        api.getReasoningFeedback(traceId),
      ]);
      setTrace(traceData as Record<string, unknown>);
      setFeedback(Array.isArray(feedbackData) ? feedbackData : []);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('reasoning.errors.load_trace', { defaultValue: '推理详情加载失败' }));
      setTrace(null);
    } finally {
      setLoading(false);
    }
  }, [traceId, t]);

  useEffect(() => { void load(); }, [load]);

  const sendFeedback = async (thumbs: 'up' | 'down') => {
    if (submitting) return;
    setSubmitting(true);
    setError('');
    try {
      await api.submitReasoningFeedback(traceId, { rating: thumbs === 'up' ? 1 : 0, thumbs });
      setSubmitted(thumbs);
      const list = await api.getReasoningFeedback(traceId);
      setFeedback(Array.isArray(list) ? list : []);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('reasoning.errors.feedback_failed', { defaultValue: '反馈提交失败' }));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p role="status" className="mt-4 text-xs text-[var(--color-text-muted)]">{t('common.loading')}</p>;

  return (
    <section aria-label={t('reasoning.trace_detail', { defaultValue: '推理详情' })} className="mt-4 border-t border-[var(--color-border-subtle)] pt-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('reasoning.trace_detail', { defaultValue: '推理详情' })}</h4>
        <div className="flex items-center gap-1">
          <Button
            variant={submitted === 'up' ? 'secondary' : 'ghost'}
            size="xs"
            disabled={submitting}
            aria-label={t('reasoning.feedback_up', { defaultValue: '赞' })}
            aria-pressed={submitted === 'up'}
            onClick={() => void sendFeedback('up')}
          >
            <ThumbsUp size={14} />
          </Button>
          <Button
            variant={submitted === 'down' ? 'secondary' : 'ghost'}
            size="xs"
            disabled={submitting}
            aria-label={t('reasoning.feedback_down', { defaultValue: '踩' })}
            aria-pressed={submitted === 'down'}
            onClick={() => void sendFeedback('down')}
          >
            <ThumbsDown size={14} />
          </Button>
        </div>
      </div>
      {error && <p role="alert" className="mb-2 text-xs text-[var(--color-error)]">{error}</p>}
      {trace && (
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3 text-xs text-[var(--color-text-secondary)]">
          {typeof trace.answer === 'string' && trace.answer
            ? trace.answer
            : JSON.stringify(trace, null, 2)}
        </pre>
      )}
      {feedback.length > 0 && (
        <ul className="mt-3 space-y-1">
          {feedback.map((entry, index) => (
            <li key={index} className="text-xs text-[var(--color-text-muted)]">
              {typeof entry.thumbs === 'string'
                ? (entry.thumbs === 'up'
                  ? t('reasoning.feedback_up', { defaultValue: '赞' })
                  : t('reasoning.feedback_down', { defaultValue: '踩' }))
                : null}
              {typeof entry.comment === 'string' && entry.comment ? ` ${entry.comment}` : ''}
              {typeof entry.rating === 'number' ? ` (${entry.rating})` : ''}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
