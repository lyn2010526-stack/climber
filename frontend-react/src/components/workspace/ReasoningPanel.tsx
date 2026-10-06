import { useState, useCallback } from 'react';
import {
  Brain, GitBranch, Target, Shield, AlertTriangle, CheckCircle2,
  ChevronDown, ChevronRight, Zap, MessageSquare, Scale, Loader2,
  ThumbsUp, ThumbsDown, Star,
} from 'lucide-react';
import { api, type ReasoningModeOut, type ReasoningResultOut } from '../../api';
import { useI18n } from '../../i18n';
import { formatDuration } from '../../lib/duration';

/** The strategies the mode selector offers, each with the key that names it. */
const REASONING_MODES = [
  { id: 'auto', labelKey: 'reasoning.mode.auto' },
  { id: 'tree', labelKey: 'reasoning.mode.tree' },
  { id: 'deep', labelKey: 'reasoning.mode.deep' },
  { id: 'debate', labelKey: 'reasoning.mode.debate' },
] as const;

/** Path-count options, so the count and its noun are translated together. */
const PATH_OPTIONS = [1, 2, 3, 5] as const;
const ROUND_OPTIONS = [1, 2, 3, 5] as const;

/**
 * The three strategies described in the empty state. They name the options the
 * selector offers; the backend's own mode list is reported separately so the two
 * are never conflated.
 */
const STRATEGY_BLURBS = [
  { id: 'tree', tone: 'text-[var(--color-success)]', labelKey: 'reasoning.mode.tree', hintKey: 'reasoning.strategy.tree' },
  { id: 'deep', tone: 'text-[var(--color-info)]', labelKey: 'reasoning.mode.deep', hintKey: 'reasoning.strategy.deep' },
  { id: 'debate', tone: 'text-[var(--color-warning)]', labelKey: 'reasoning.mode.debate', hintKey: 'reasoning.strategy.debate' },
] as const;

type ReasoningMode = ReasoningModeOut;
type ReasoningResult = ReasoningResultOut;

export function ReasoningPanel() {
  const { t } = useI18n();
  const [task, setTask] = useState('');
  const [mode, setMode] = useState('auto');
  const [maxPaths, setMaxPaths] = useState(3);
  const [maxRounds, setMaxRounds] = useState(3);
  const [coverageEnabled, setCoverageEnabled] = useState(true);
  const [modes, setModes] = useState<ReasoningMode[]>([]);
  /**
   * The mode options below are hard-coded, not fetched. When the modes request
   * fails the list is not silently treated as "the backend offers these four":
   * the panel discloses that the options on screen are built-in.
   */
  const [modesError, setModesError] = useState<string | null>(null);
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackThumbs, setFeedbackThumbs] = useState<'up' | 'down' | null>(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const loadModes = useCallback(async () => {
    setModesError(null);
    try {
      const data = await api.listReasoningModes();
      setModes(data);
    } catch (e) {
      setModesError(e instanceof Error ? e.message : t('reasoning.errors.load_modes'));
    }
  }, [t]);

  const handleReason = async () => {
    if (!task.trim()) return;
    setIsRunning(true);
    setError(null);
    setResult(null);
    // A new run is a fresh subject: feedback entered for the previous result
    // must not carry over (R12-N06).
    setFeedbackRating(0);
    setFeedbackThumbs(null);
    setFeedbackComment('');
    setFeedbackSubmitted(false);
    setFeedbackError(null);

    if (modes.length === 0) await loadModes();

    try {
      const data = await api.reasonStream(task, mode, maxPaths, maxRounds, coverageEnabled);
      setResult(data);
    } catch (err: any) {
      setError(err.message || t('reasoning.errors.failed'));
    } finally {
      setIsRunning(false);
    }
  };

  const togglePathExpand = (id: string) => {
    setExpandedPaths(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleFeedback = async () => {
    if (!result?.trace?.trace_id || feedbackRating === 0 || feedbackSubmitting) return;
    setFeedbackSubmitting(true);
    setFeedbackError(null);
    try {
      const feedback: { rating: number; thumbs?: string; comment?: string } = {
        rating: feedbackRating,
        comment: feedbackComment,
      };
      if (feedbackThumbs !== undefined && feedbackThumbs !== null) {
        feedback['thumbs'] = feedbackThumbs;
      }
      await api.submitReasoningFeedback(result.trace.trace_id, feedback);
      setFeedbackSubmitted(true);
    } catch {
      setFeedbackError(t('reasoning.errors.feedback_failed'));
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const getModeIcon = (modeId: string) => {
    switch (modeId) {
      case 'tree': return <GitBranch size={14} />;
      case 'deep': return <Zap size={14} />;
      case 'debate': return <Scale size={14} />;
      default: return <Brain size={14} />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg-base)]">
      {/* Input Section */}
      <div className="p-4 border-b border-[var(--color-border-subtle)] space-y-3">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-[var(--color-accent-foreground)]" />
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('reasoning.title')}</h3>
        </div>

        <textarea
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder={t('reasoning.task_placeholder')}
          aria-label={t('reasoning.task_placeholder')}
          className="w-full px-3 py-2 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-lg text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-border-accent)] resize-none"
          rows={3}
        />

        {/* Three parameters share one compact row, so each carries a
            screen-reader-only label instead of a visible one. Without it a
            combobox announced only its selected option, which left the user
            guessing what the control changed. */}
        <div className="flex gap-2">
          <label className="sr-only" htmlFor="reasoning-mode">{t('reasoning.mode_label')}</label>
          <select
            id="reasoning-mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-accent)]"
          >
            {REASONING_MODES.map(option => (
              <option key={option.id} value={option.id}>{t(option.labelKey)}</option>
            ))}
          </select>
          <label className="sr-only" htmlFor="reasoning-paths">{t('reasoning.paths_label')}</label>
          <select
            id="reasoning-paths"
            value={maxPaths}
            onChange={(e) => setMaxPaths(Number(e.target.value))}
            className="px-2 py-1.5 bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)] rounded text-xs text-[var(--color-text-primary)] focus:outline-none"
          >
            {PATH_OPTIONS.map(count => (
              <option key={count} value={count}>{t('reasoning.paths_option', { count })}</option>
            ))}
          </select>
          <label className="sr-only" htmlFor="reasoning-rounds">{t('reasoning.rounds_label')}</label>
          <select
            id="reasoning-rounds"
            value={maxRounds}
            onChange={(e) => setMaxRounds(Number(e.target.value))}
            className="px-2 py-1.5 bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)] rounded text-xs text-[var(--color-text-primary)] focus:outline-none"
          >
            {ROUND_OPTIONS.map(count => (
              <option key={count} value={count}>{t('reasoning.rounds_option', { count })}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)] cursor-pointer">
            <input
              type="checkbox"
              checked={coverageEnabled}
              onChange={(e) => setCoverageEnabled(e.target.checked)}
              className="rounded border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] text-[var(--color-accent-foreground)] focus:ring-[var(--color-accent-foreground)]/30"
            />
             {t('reasoning.coverage_check')}
          </label>

          <button type="button"
            onClick={handleReason}
            disabled={isRunning || !task.trim()}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:bg-[var(--color-bg-surface-2)] disabled:text-[var(--color-text-muted)] text-[var(--color-accent-text)] rounded-lg text-xs font-medium transition-all"
          >
            {isRunning ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
             {isRunning ? t('reasoning.running_action') : t('reasoning.run_action')}
          </button>
        </div>
      </div>

      {/* Results Section */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {error && (
          <div className="p-3 bg-[var(--color-error)] border border-[var(--color-error)] rounded-lg text-xs text-[var(--color-error)]">
            <AlertTriangle size={12} className="inline mr-1" />
            {error}
          </div>
        )}

        {!result && !isRunning && (
          <div className="text-center py-8 text-[var(--color-text-muted)] text-xs">
            <Brain size={32} className="mx-auto mb-3 opacity-30" />
             <p>{t('reasoning.idle_hint')}</p>
             <div className="mt-4 space-y-1 text-left px-4">
               <p className="text-[var(--color-text-secondary)] font-medium">{t('reasoning.strategies_label')}</p>
               {/* The strategies named here are the ones the selector offers;
                   the backend's own mode list is reported separately so the two
                   are never conflated. */}
               {modesError ? (
                 <p className="pl-2 text-[var(--color-text-muted)]" role="status">
                   {t('reasoning.modes_not_reported', { detail: modesError })}
                 </p>
               ) : (
                 <>
                   {STRATEGY_BLURBS.map(strategy => (
                     <p key={strategy.id} className="pl-2">
                       <span className={strategy.tone}>{t(strategy.labelKey)}</span>
                       {' — '}
                       {t(strategy.hintKey)}
                     </p>
                   ))}
                 </>
               )}
             </div>
          </div>
        )}

        {isRunning && (
          <div className="flex flex-col items-center justify-center py-12 text-[var(--color-text-secondary)]">
            <Loader2 size={32} className="animate-spin mb-3 text-[var(--color-accent-foreground)]" />
             <p className="text-sm">{t('reasoning.in_progress')}</p>
             <p className="text-xs mt-1 text-[var(--color-text-muted)]">
               {t('reasoning.progress_line', { mode, paths: maxPaths, rounds: maxRounds })}
             </p>
          </div>
        )}

        {result && !isRunning && (
          <>
            {/* Summary */}
            <div className="p-3 bg-[var(--color-bg-surface-1)] rounded-lg border border-[var(--color-border-subtle)]">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                 <span className="text-xs font-medium text-[var(--color-text-primary)]">{t('reasoning.completed')}</span>
                <span className="ml-auto text-xs text-[var(--color-text-muted)]">{formatDuration(result.total_duration_ms, 'ms')}</span>
              </div>
              <div className="flex gap-3 text-xs text-[var(--color-text-secondary)]">
                <span className="flex items-center gap-1">{getModeIcon(result.mode_used)} {result.mode_used}</span>
                 <span>{t('reasoning.candidate_count', { count: result.candidates.length })}</span>
                 {result.coverage && <span>{t('reasoning.coverage_score', { score: (result.coverage.score * 100).toFixed(0) })}</span>}
              </div>
            </div>

            {/* Coverage Dashboard */}
            {result.coverage && result.coverage.score > 0 && (
              <div className="p-3 bg-[var(--color-bg-surface-1)] rounded-lg border border-[var(--color-border-subtle)]">
                <div className="flex items-center gap-2 mb-2">
                  <Shield size={13} className="text-[var(--color-info)]" />
                   <span className="text-xs font-medium text-[var(--color-text-primary)]">{t('reasoning.coverage_report')}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center justify-between p-2 bg-[var(--color-bg-base)] rounded">
                     <span className="text-[var(--color-text-secondary)]">{t('reasoning.coverage.edge_cases')}</span>
                    <span className="text-[var(--color-text-primary)] font-mono">{result.coverage.edge_cases_count}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-[var(--color-bg-base)] rounded">
                     <span className="text-[var(--color-text-secondary)]">{t('reasoning.coverage.risks')}</span>
                    <span className="text-[var(--color-text-primary)] font-mono">{result.coverage.risks_count}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-[var(--color-bg-base)] rounded">
                     <span className="text-[var(--color-text-secondary)]">{t('reasoning.coverage.assumptions')}</span>
                    <span className="text-[var(--color-text-primary)] font-mono">{result.coverage.assumptions_count}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-[var(--color-bg-base)] rounded">
                     <span className="text-[var(--color-text-secondary)]">{t('reasoning.coverage.blind_spots')}</span>
                    <span className="text-[var(--color-text-primary)] font-mono">{result.coverage.blind_spots_count}</span>
                  </div>
                </div>
                {result.coverage.high_risks > 0 && (
                  <div className="mt-2 p-2 bg-[var(--color-error)] border border-[var(--color-error)] rounded text-xs text-[var(--color-error)]">
                    <AlertTriangle size={11} className="inline mr-1" />
                     {t('reasoning.coverage.high_risks', { count: result.coverage.high_risks })}
                  </div>
                )}
              </div>
            )}

            {/* Path Comparison */}
            {result.trace?.path_traces && result.trace.path_traces.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-[var(--color-text-secondary)]">
                  <GitBranch size={13} />
                   <span>{t('reasoning.path_comparison')}</span>
                </div>
                {result.trace.path_traces.map((path) => (
                  <div key={path.candidate_id} className="bg-[var(--color-bg-surface-1)] rounded-lg border border-[var(--color-border-subtle)] overflow-hidden">
                    <button type="button"
                      onClick={() => togglePathExpand(path.candidate_id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-[var(--color-bg-surface-2)]"
                    >
                      {expandedPaths.has(path.candidate_id) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      <span className="text-[var(--color-accent-foreground)] font-mono">{path.path_type}</span>
                      <span className="ml-auto text-[var(--color-text-secondary)]">
                        {path.final_confidence != null ? `${(path.final_confidence * 100).toFixed(0)}%` : '—'}
                      </span>
                    </button>
                    {expandedPaths.has(path.candidate_id) && (
                      <div className="border-t border-[var(--color-border-subtle)] p-2 space-y-1">
                        {path.rounds.map((round) => (
                          <div key={round.round_num} className="flex items-start gap-2 text-xs">
                            <span className="text-[var(--color-text-muted)] font-mono w-14 shrink-0">R{round.round_num} {round.action}</span>
                            <span className="text-[var(--color-text-secondary)]">{round.output_summary}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Best Answer */}
            <div className="p-3 bg-[var(--color-bg-surface-1)] rounded-lg border border-[var(--color-border-accent)]">
              <div className="flex items-center gap-2 mb-2">
                <Target size={13} className="text-[var(--color-accent-foreground)]" />
                 <span className="text-xs font-medium text-[var(--color-text-primary)]">{t('reasoning.best_answer')}</span>
              </div>
              <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap max-h-64 overflow-y-auto">
                {result.answer}
              </div>
            </div>

            {/* Feedback Section */}
            {!feedbackSubmitted ? (
              <div className="p-3 bg-[var(--color-bg-surface-1)]/50 rounded-lg border border-[var(--color-border-subtle)]/50 space-y-2">
                 <span className="text-xs font-medium text-[var(--color-text-secondary)]">{t('reasoning.rate_this')}</span>
                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button type="button"
                        key={star}
                        onClick={() => setFeedbackRating(star)}
                        className={`p-1 rounded ${feedbackRating >= star ? 'text-[var(--color-warning)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'}`}
                      >
                        <Star size={14} fill={feedbackRating >= star ? 'currentColor' : 'none'} />
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button type="button"
                      onClick={() => setFeedbackThumbs(feedbackThumbs === 'up' ? null : 'up')}
                      className={`p-1 rounded ${feedbackThumbs === 'up' ? 'text-[var(--color-success)] bg-[var(--color-success)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'}`}
                    >
                      <ThumbsUp size={14} />
                    </button>
                    <button type="button"
                      onClick={() => setFeedbackThumbs(feedbackThumbs === 'down' ? null : 'down')}
                      className={`p-1 rounded ${feedbackThumbs === 'down' ? 'text-[var(--color-error)] bg-[var(--color-error)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'}`}
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </div>
                </div>
                <textarea
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                   placeholder={t('reasoning.feedback_placeholder')}
                  className="w-full px-2 py-1 bg-[var(--color-bg-base)] border border-[var(--color-border-subtle)] rounded text-xs text-[var(--color-text-secondary)] placeholder:text-[var(--color-text-muted)] focus:outline-none resize-none"
                  rows={2}
                />
                {feedbackError && (
                  <p role="alert" className="text-xs text-[var(--color-error)]">{feedbackError}</p>
                )}
                <button type="button"
                  onClick={handleFeedback}
                  disabled={feedbackRating === 0 || feedbackSubmitting}
                  className="px-3 py-1 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:bg-[var(--color-bg-surface-2)] disabled:text-[var(--color-text-muted)] text-[var(--color-accent-text)] text-xs rounded transition-colors"
                >
                   {feedbackSubmitting ? t('reasoning.submitting_feedback') : t('reasoning.submit_feedback')}
                </button>
              </div>
            ) : (
              <div className="p-2 bg-[var(--color-success)] rounded-lg border border-[var(--color-success)] text-xs text-[var(--color-success)] text-center">
                 {t('reasoning.feedback_thanks')}
              </div>
            )}

            {/* Selection Reason */}
            {result.trace?.final_selection_reason && (
              <div className="p-3 bg-[var(--color-bg-surface-1)] rounded-lg border border-[var(--color-border-subtle)]">
                <div className="flex items-center gap-2 mb-1">
                  <MessageSquare size={13} className="text-[var(--color-text-secondary)]" />
                   <span className="text-xs font-medium text-[var(--color-text-secondary)]">{t('reasoning.selection_reason')}</span>
                </div>
                <p className="text-xs text-[var(--color-text-secondary)]">{result.trace.final_selection_reason}</p>
              </div>
            )}

            {/* Candidate List */}
            {result.candidates.length > 1 && (
              <div className="space-y-2">
                 <span className="text-xs font-medium text-[var(--color-text-secondary)]">{t('reasoning.all_candidates', { count: result.candidates.length })}</span>
                {result.candidates.map((c) => (
                  <div key={c.id} className="p-2 bg-[var(--color-bg-surface-1)] rounded border border-[var(--color-border-subtle)] text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[var(--color-accent-foreground)] font-mono">{c.path_type || c.strategy}</span>
                      <span className="text-[var(--color-text-secondary)]">{(c.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-[var(--color-text-muted)] line-clamp-2">{c.content?.slice(0, 150)}...</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
