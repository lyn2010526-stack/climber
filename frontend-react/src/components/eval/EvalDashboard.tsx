import { useEffect, useState, useCallback } from 'react';
import { api } from '../../api';
import { useI18n } from '../../i18n';

/**
 * `POST /eval/run` records a run summary; it does not execute the dataset. The
 * caller supplies every counter, so a run whose `total_cases` is 0 reports
 * "nothing was evaluated" — the UI must not present that as a 0% pass rate.
 */
interface EvalDataset {
  id: string;
  name: string;
  description: string;
  case_count: number;
  created_at: string;
}

interface EvalRunResult {
  case_id: string;
  score: number;
  passed: boolean;
  reasoning: string;
}

interface EvalRun {
  id: string;
  dataset_id: string;
  agent_id: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  average_score: number;
  pass_rate: number;
  /**
   * The backend stores per-case detail in `results_json` and omits it from the
   * response, so this is usually absent. Absent means "the API returned no
   * per-case detail", which is not the same as "no cases failed".
   */
  results?: EvalRunResult[];
  created_at: string;
}

interface EvalAgent {
  id: string;
  name: string;
}

function errorMessage(e: unknown, fallback: string): string {
  return e instanceof Error && e.message ? e.message : fallback;
}

export function EvalDashboard() {
  const { t } = useI18n();
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [agents, setAgents] = useState<EvalAgent[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  /** Datasets and agents are two independent requests; one failing must not
   *  blank the other or leave an empty list reading as "none exist". */
  const [datasetsError, setDatasetsError] = useState<string | null>(null);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState<string>('');

  const fetchDatasets = useCallback(async () => {
    setDatasetsError(null);
    try {
      setDatasets(await api.listEvalDatasets());
    } catch (e) {
      setDatasets([]);
      setDatasetsError(errorMessage(e, t('eval.errors.load_datasets')));
    }
  }, [t]);

  const fetchAgents = useCallback(async () => {
    setAgentsError(null);
    try {
      const data = await api.listAgents();
      setAgents(data);
      if (data.length > 0) setSelectedAgent(current => current || data[0].id);
    } catch (e) {
      setAgents([]);
      setAgentsError(errorMessage(e, t('eval.errors.load_agents')));
    }
  }, [t]);

  const runEval = async () => {
    if (!selectedDataset || !selectedAgent) {
      setError(t('eval.errors.select_both'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api.runEvaluation(selectedDataset, selectedAgent);
      setRuns(current => [result, ...current]);
    } catch (e) {
      setError(errorMessage(e, t('eval.errors.run_failed')));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
    fetchAgents();
    setInitialLoading(false);
  }, [fetchAgents, fetchDatasets]);

  return (
    <div className="p-6 bg-[var(--color-bg-page)] text-[var(--color-text-primary)] min-h-full">
      <div className="flex items-center justify-between mb-6">
         <h2 className="text-xl font-bold">{t('eval.title')}</h2>
      </div>

      {error && <div className="text-[var(--color-error)] text-sm mb-4">{error}</div>}

      {/* Datasets */}
      <div className="mb-6">
           <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">{t('eval.datasets')}</h3>
         {initialLoading ? (
            <div role="status" className="text-[var(--color-text-muted)] text-sm">{t('common.loading')}</div>
        ) : datasetsError ? (
            <div role="alert" className="text-[var(--color-error)] text-sm">
              {t('eval.datasets_not_reported', { detail: datasetsError })}
            </div>
        ) : datasets.length === 0 ? (
            <div className="text-[var(--color-text-muted)] text-sm">{t('eval.datasets_empty')}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {datasets.map((ds) => (
              <div
                key={ds.id}
                onClick={() => setSelectedDataset(ds.id)}
                className={`p-3 rounded-lg border cursor-pointer transition ${
                  selectedDataset === ds.id
                    ? 'border-[var(--color-info)] bg-[var(--color-info)]'
                    : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] hover:border-[var(--color-border-default)]'
                }`}
              >
                <div className="font-medium text-sm">{ds.name}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">{ds.description}</div>
                 <div className="text-xs text-[var(--color-text-muted)] mt-2">
                   {typeof ds.case_count === 'number'
                     ? t('eval.dataset_case_count', { count: ds.case_count })
                     : t('common.not_reported')}
                 </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mb-6">
        <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">{t('eval.agents')}</h3>
        {agentsError ? (
          <div role="alert" className="text-[var(--color-error)] text-sm">{t('eval.agents_not_reported', { detail: agentsError })}</div>
        ) : (
          <select
            value={selectedAgent}
            onChange={(event) => setSelectedAgent(event.target.value)}
            className="w-full max-w-sm px-3 py-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] text-sm"
          >
            <option value="">{t('eval.select_agent')}</option>
            {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
          </select>
        )}
      </div>

      {selectedDataset && selectedAgent && (
        <button type="button"
          onClick={runEval}
          disabled={loading}
           className="mb-6 px-4 py-2 bg-[var(--color-info)] text-[var(--color-text-inverse)] hover:bg-[var(--color-info)] rounded text-sm font-medium disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)]"
        >
           {loading ? t('eval.running') : t('eval.run')}
        </button>
      )}

      {/* Results */}
      {runs.length > 0 && (
         <div>
           <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">{t('eval.results')}</h3>
          <div className="space-y-3">
            {runs.map((run) => {
              // A run that reports zero cases executed has no pass rate, no
              // pass count and no average to show. Rendering 0 and 0% would
              // report a clean failure that the backend never evaluated.
              const executed = typeof run.total_cases === 'number' && run.total_cases > 0;
              const passRate = typeof run.pass_rate === 'number' ? run.pass_rate : null;
              const average = typeof run.average_score === 'number' ? run.average_score : null;
              return (
               <div key={run.id} className="p-4 bg-[var(--color-bg-surface)] rounded-lg border border-[var(--color-border-subtle)]">
                <div className="flex items-center justify-between mb-2">
                   <span className="text-sm font-medium">{t('eval.run_label', { id: run.id.slice(0, 8) })}</span>
                   <span className="text-xs text-[var(--color-text-muted)]">{run.created_at?.slice(0, 19) || t('common.not_reported')}</span>
                </div>
                {!executed ? (
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {t('eval.run_no_cases', { total: run.total_cases ?? t('common.not_reported') })}
                  </p>
                ) : (
                  <div className="grid grid-cols-4 gap-3 mb-3">
                    <div className="text-center">
                      <div className="text-lg font-bold text-[var(--color-success)]">
                        {run.passed_cases ?? t('common.not_reported')}
                      </div>
                      <div className="text-xs text-[var(--color-text-muted)]">{t('eval.passed')}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-[var(--color-error)]">
                        {run.failed_cases ?? t('common.not_reported')}
                      </div>
                      <div className="text-xs text-[var(--color-text-muted)]">{t('eval.failed')}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-[var(--color-info)]">
                        {passRate === null ? t('common.not_reported') : `${(passRate * 100).toFixed(0)}%`}
                      </div>
                      <div className="text-xs text-[var(--color-text-muted)]">{t('eval.pass_rate')}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-[var(--color-accent-foreground)]">
                        {average === null ? t('common.not_reported') : average.toFixed(2)}
                      </div>
                      <div className="text-xs text-[var(--color-text-muted)]">{t('eval.average_score')}</div>
                    </div>
                  </div>
                )}
                {run.results && run.results.length > 0 ? (
                  <div className="space-y-1 mt-2">
                    {run.results.map((r) => (
                      <div key={r.case_id} className="flex items-center gap-2 text-xs">
                        <span className={r.passed ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}>
                           {r.passed ? t('eval.passed') : t('eval.failed')}
                        </span>
                         <span className="text-[var(--color-text-muted)]">{r.case_id}</span>
                         <span className="text-[var(--color-text-muted)]">
                           {typeof r.score === 'number' ? r.score.toFixed(2) : t('common.not_reported')}
                         </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[var(--color-text-muted)] mt-2">{t('eval.no_case_results')}</p>
                )}
              </div>
            );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default EvalDashboard;
