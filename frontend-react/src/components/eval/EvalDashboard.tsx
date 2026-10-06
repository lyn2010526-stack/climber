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

/** One editable rubric row in the quick-check tool. Keywords are comma lists. */
interface RubricRow {
  description: string;
  contains_any: string;
  not_contains_any: string;
  essential: boolean;
  veto: boolean;
}

interface AssessVerdict {
  item_id: string;
  passed: boolean;
  reason: string;
  weight: number;
}

interface AssessResult {
  score: number;
  passed: boolean;
  verdicts: AssessVerdict[];
  failure_reasons: string[];
  judge: string;
}

function splitKeywords(value: string): string[] {
  return value.split(',').map(k => k.trim()).filter(Boolean);
}

function EvalQuickAssess() {
  const { t } = useI18n();
  const [output, setOutput] = useState('');
  const [rows, setRows] = useState<RubricRow[]>([
    { description: '', contains_any: '', not_contains_any: '', essential: true, veto: false },
    { description: '', contains_any: '', not_contains_any: '', essential: false, veto: false },
  ]);
  const [result, setResult] = useState<AssessResult | null>(null);
  const [assessing, setAssessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateRow = (index: number, patch: Partial<RubricRow>) => {
    setRows(current => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const runAssess = async () => {
    setError(null);
    const content = output.trim();
    if (!content) {
      setError(t('eval.assess.empty_output'));
      return;
    }
    const rubric = rows
      .map((row, index) => ({
        item_id: `item-${index + 1}`,
        description: row.description,
        contains_any: splitKeywords(row.contains_any),
        not_contains_any: splitKeywords(row.not_contains_any),
        essential: row.essential,
        veto: row.veto,
      }))
      .filter(row => row.description.trim() || row.contains_any.length > 0 || row.not_contains_any.length > 0);
    if (rubric.length === 0) {
      setError(t('eval.assess.empty_rubric'));
      return;
    }
    setAssessing(true);
    try {
      setResult(await api.evaluateOutput({ output: content, rubric }));
    } catch (e) {
      setResult(null);
      setError(errorMessage(e, t('eval.assess.failed')));
    } finally {
      setAssessing(false);
    }
  };

  const rowInput = 'w-full px-2 py-1.5 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] text-sm';

  return (
    <div className="mb-6">
      <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">{t('eval.assess.title')}</h3>
      <div className="p-4 bg-[var(--color-bg-surface)] rounded-lg border border-[var(--color-border-subtle)] space-y-3">
        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">{t('eval.assess.output_label')}</label>
          <textarea
            value={output}
            onChange={e => setOutput(e.target.value)}
            rows={3}
            className={`${rowInput} resize-y`}
            placeholder={t('eval.assess.output_placeholder')}
          />
        </div>

        <div>
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">{t('eval.assess.rubric_label')}</label>
          <div className="space-y-2">
            {rows.map((row, index) => (
              <div key={index} className="grid grid-cols-12 gap-2 items-center">
                <input
                  value={row.description}
                  onChange={e => updateRow(index, { description: e.target.value })}
                  className={`${rowInput} col-span-4`}
                  placeholder={t('eval.assess.description_placeholder')}
                  aria-label={t('eval.assess.description_placeholder')}
                />
                <input
                  value={row.contains_any}
                  onChange={e => updateRow(index, { contains_any: e.target.value })}
                  className={`${rowInput} col-span-3`}
                  placeholder={t('eval.assess.contains_placeholder')}
                  aria-label={t('eval.assess.contains_placeholder')}
                />
                <input
                  value={row.not_contains_any}
                  onChange={e => updateRow(index, { not_contains_any: e.target.value })}
                  className={`${rowInput} col-span-3`}
                  placeholder={t('eval.assess.not_contains_placeholder')}
                  aria-label={t('eval.assess.not_contains_placeholder')}
                />
                <label className="col-span-1 flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
                  <input type="checkbox" checked={row.essential} onChange={e => updateRow(index, { essential: e.target.checked })} />
                  {t('eval.assess.essential')}
                </label>
                <button
                  type="button"
                  onClick={() => setRows(current => current.filter((_, i) => i !== index))}
                  className="col-span-1 text-xs text-[var(--color-error)]"
                  aria-label={t('eval.assess.remove_item')}
                >
                  {t('eval.assess.remove_item')}
                </button>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setRows(current => [...current, { description: '', contains_any: '', not_contains_any: '', essential: false, veto: false }])}
            className="mt-2 text-xs text-[var(--color-info)]"
          >
            {t('eval.assess.add_item')}
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={runAssess}
            disabled={assessing}
            className="px-4 py-2 bg-[var(--color-info)] text-[var(--color-text-inverse)] rounded text-sm font-medium disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)]"
          >
            {assessing ? t('eval.assess.running') : t('eval.assess.run')}
          </button>
          {error && <span role="alert" className="text-[var(--color-error)] text-sm">{error}</span>}
        </div>

        {result && (
          <div className="pt-2 border-t border-[var(--color-border-subtle)]">
            <div className="flex items-center gap-3 mb-2">
              <span className={`text-sm font-semibold ${result.passed ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
                {result.passed ? t('eval.assess.passed') : t('eval.assess.failed')}
              </span>
              <span className="text-sm text-[var(--color-text-muted)]">
                {t('eval.assess.score', { score: (result.score * 100).toFixed(0) })}
              </span>
              <span className="text-xs text-[var(--color-text-muted)]">{result.judge}</span>
            </div>
            {result.verdicts.map(verdict => (
              <div key={verdict.item_id} className="flex items-start gap-2 text-xs py-0.5">
                <span className={verdict.passed ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}>
                  {verdict.passed ? 'PASS' : 'FAIL'}
                </span>
                <span className="text-[var(--color-text-muted)] flex-1">
                  {verdict.item_id}
                  {verdict.reason ? ` — ${verdict.reason}` : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface EvalReportSummary {
  report_id: string;
  created_at: string;
  total_scenarios: number;
  passed_scenarios: number;
  average_score: number;
  pass_at_k: Record<string, number> | null;
  pass_hat_k: Record<string, number> | null;
  total_tokens: number;
  duration_ms: number;
}

function EvalReports() {
  const { t } = useI18n();
  const [reports, setReports] = useState<EvalReportSummary[]>([]);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [reportsLoading, setReportsLoading] = useState(true);

  useEffect(() => {
    api.listEvalReports()
      .then(data => setReports(Array.isArray(data) ? data : []))
      .catch(e => setReportsError(errorMessage(e, t('eval.reports.failed'))))
      .finally(() => setReportsLoading(false));
  }, [t]);

  return (
    <div className="mb-6">
      <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">{t('eval.reports.title')}</h3>
      {reportsLoading ? (
        <div role="status" className="text-[var(--color-text-muted)] text-sm">{t('common.loading')}</div>
      ) : reportsError ? (
        <div role="alert" className="text-[var(--color-error)] text-sm">{t('eval.reports.error', { detail: reportsError })}</div>
      ) : reports.length === 0 ? (
        <div className="text-[var(--color-text-muted)] text-sm">{t('eval.reports.empty')}</div>
      ) : (
        <div className="space-y-2">
          {reports.map(report => {
            const passFirstKey = report.pass_at_k ? Object.keys(report.pass_at_k)[0] : undefined;
            const passFirstValue = (passFirstKey !== undefined ? report.pass_at_k?.[passFirstKey] : undefined) ?? null;
            return (
              <div key={report.report_id} className="p-3 bg-[var(--color-bg-surface)] rounded-lg border border-[var(--color-border-subtle)] text-sm">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium">{report.report_id.slice(0, 8)}</span>
                  <span className="text-xs text-[var(--color-text-muted)]">{report.created_at?.slice(0, 19) || t('common.not_reported')}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-[var(--color-text-muted)]">
                  <span>{t('eval.reports.scenarios', { total: report.total_scenarios, passed: report.passed_scenarios })}</span>
                  <span>{t('eval.reports.average', { score: typeof report.average_score === 'number' ? report.average_score.toFixed(2) : t('common.not_reported') })}</span>
                  {passFirstKey !== undefined && passFirstValue !== null && (
                    <span>{t('eval.reports.pass_at_k', { k: passFirstKey, v: (passFirstValue * 100).toFixed(0) })}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
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
  const [showCreateDataset, setShowCreateDataset] = useState(false);
  const [newDatasetName, setNewDatasetName] = useState('');
  const [newDatasetDescription, setNewDatasetDescription] = useState('');
  const [newDatasetCases, setNewDatasetCases] = useState('[]');
  const [creatingDataset, setCreatingDataset] = useState(false);
  const [createDatasetError, setCreateDatasetError] = useState<string | null>(null);

  const createDataset = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newDatasetName.trim() || creatingDataset) return;
    setCreatingDataset(true);
    setCreateDatasetError(null);
    try {
      await api.createEvalDataset({
        name: newDatasetName.trim(),
        description: newDatasetDescription.trim() || undefined,
        data_json: newDatasetCases.trim() || '[]',
      });
      setShowCreateDataset(false);
      setNewDatasetName('');
      setNewDatasetDescription('');
      setNewDatasetCases('[]');
      await fetchDatasets();
    } catch (e) {
      setCreateDatasetError(errorMessage(e, t('eval.errors.create_dataset', { defaultValue: 'Failed to create dataset' })));
    } finally {
      setCreatingDataset(false);
    }
  };

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
      if (data.length > 0) setSelectedAgent(current => current || (data[0]?.id ?? ''));
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
    // Keep the datasets section in its loading state until both fetches
    // settle; firing the requests and then immediately clearing the flag left
    // "loading" ending before any data was on screen (R12-H59).
    void Promise.allSettled([fetchDatasets(), fetchAgents()]).then(() => {
      setInitialLoading(false);
    });
  }, [fetchAgents, fetchDatasets]);

  return (
    <div className="p-6 bg-[var(--color-bg-page)] text-[var(--color-text-primary)] min-h-full">
      <div className="flex items-center justify-between mb-6">
         <h2 className="text-xl font-bold">{t('eval.title')}</h2>
      </div>

      {error && <div className="text-[var(--color-error)] text-sm mb-4">{error}</div>}

      {/* Datasets */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
           <h3 className="text-sm font-semibold text-[var(--color-text-muted)]">{t('eval.datasets')}</h3>
          <button
            type="button"
            onClick={() => setShowCreateDataset(current => !current)}
            aria-expanded={showCreateDataset}
            className="text-xs text-[var(--color-info)] hover:underline"
          >
            {t('eval.dataset_create', { defaultValue: '新建数据集' })}
          </button>
        </div>
        {showCreateDataset && (
          <form
            className="mb-3 max-w-xl space-y-2 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] p-3"
            onSubmit={(event) => void createDataset(event)}
          >
            <input
              aria-label={t('eval.dataset_name', { defaultValue: '数据集名称' })}
              placeholder={t('eval.dataset_name', { defaultValue: '数据集名称' })}
              value={newDatasetName}
              onChange={(event) => setNewDatasetName(event.target.value)}
              className="w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            />
            <input
              aria-label={t('eval.dataset_description', { defaultValue: '描述（可选）' })}
              placeholder={t('eval.dataset_description', { defaultValue: '描述（可选）' })}
              value={newDatasetDescription}
              onChange={(event) => setNewDatasetDescription(event.target.value)}
              className="w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            />
            <textarea
              aria-label={t('eval.dataset_cases', { defaultValue: '用例 JSON 数组' })}
              placeholder={t('eval.dataset_cases_placeholder', { defaultValue: '[{"input": "...", "expected": "..."}]' })}
              value={newDatasetCases}
              onChange={(event) => setNewDatasetCases(event.target.value)}
              rows={4}
              className="w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 font-mono text-xs"
            />
            {createDatasetError && <p role="alert" className="text-xs text-[var(--color-error)]">{createDatasetError}</p>}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowCreateDataset(false)}
                className="rounded px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={creatingDataset || !newDatasetName.trim()}
                className="rounded bg-[var(--color-info)] px-3 py-1.5 text-xs text-white disabled:opacity-50"
              >
                {creatingDataset ? t('common.saving') : t('common.create')}
              </button>
            </div>
          </form>
        )}
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
              <button
                key={ds.id}
                type="button"
                onClick={() => setSelectedDataset(ds.id)}
                aria-pressed={selectedDataset === ds.id}
                className={`p-3 rounded-lg border cursor-pointer text-left transition ${
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
              </button>
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

      <EvalQuickAssess />
      <EvalReports />
    </div>
  );
}

export default EvalDashboard;
