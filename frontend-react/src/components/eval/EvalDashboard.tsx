import { useEffect, useState, useCallback } from 'react';
import { api } from '../../api';

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
  results: EvalRunResult[];
  created_at: string;
}

export default function EvalDashboard() {
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [seeding, setSeeding] = useState(false);

  const fetchDatasets = useCallback(async () => {
    try {
      const data = await api.listEvalDatasets();
        setDatasets(data);
    } catch {
      // ignore
    }
  }, []);

  const seedBuiltin = async () => {
    setSeeding(true);
    setError(null);
    try {
      await api.seedBuiltinDatasets();
        await fetchDatasets();
    } catch {
      setError('Network error');
    }
    setSeeding(false);
  };

  const runEval = async () => {
    if (!selectedDataset) {
      setError('请先选择数据集');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api.runEvalDataset(selectedDataset);
        setRuns([result, ...runs]);
    } catch {
      setError('Network error');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  return (
    <div className="p-6 bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] min-h-full">
      <div className="flex items-center justify-between mb-6">
         <h2 className="text-xl font-bold">评估仪表板</h2>
        <div className="flex gap-2">
          <button
            onClick={seedBuiltin}
            disabled={seeding}
            className="px-3 py-1.5 bg-[var(--color-bg-surface)] hover:bg-[var(--color-bg-surface-hover)] rounded text-sm disabled:opacity-50"
          >
            {seeding ? '导入中...' : '导入内置数据集'}
          </button>
        </div>
      </div>

      {error && <div className="text-red-400 text-sm mb-4">{error}</div>}

      {/* Datasets */}
      <div className="mb-6">
           <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">数据集</h3>
         {datasets.length === 0 ? (
            <div className="text-[var(--color-text-muted)] text-sm">暂无数据集，请先导入内置数据集</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {datasets.map((ds) => (
              <div
                key={ds.id}
                onClick={() => setSelectedDataset(ds.id)}
                className={`p-3 rounded-lg border cursor-pointer transition ${
                  selectedDataset === ds.id
                    ? 'border-blue-500 bg-blue-900/20'
                    : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] hover:border-[var(--color-border-default)]'
                }`}
              >
                <div className="font-medium text-sm">{ds.name}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">{ds.description}</div>
                 <div className="text-xs text-[var(--color-text-muted)] mt-2">{ds.case_count} 条用例</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run button */}
      {selectedDataset && (
        <button
          onClick={runEval}
          disabled={loading}
          className="mb-6 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium disabled:opacity-50"
        >
           {loading ? '运行中...' : '运行评估'}
        </button>
      )}

      {/* Results */}
      {runs.length > 0 && (
         <div>
           <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">评估结果</h3>
          <div className="space-y-3">
            {runs.map((run) => (
               <div key={run.id} className="p-4 bg-[var(--color-bg-surface)] rounded-lg border border-[var(--color-border-subtle)]">
                <div className="flex items-center justify-between mb-2">
                   <span className="text-sm font-medium">运行 {run.id.slice(0, 8)}</span>
                   <span className="text-xs text-[var(--color-text-muted)]">{run.created_at?.slice(0, 19)}</span>
                </div>
                <div className="grid grid-cols-4 gap-3 mb-3">
                  <div className="text-center">
                    <div className="text-lg font-bold text-green-400">{run.passed_cases}</div>
                      <div className="text-xs text-[var(--color-text-muted)]">通过</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-red-400">{run.failed_cases}</div>
                      <div className="text-xs text-[var(--color-text-muted)]">失败</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-blue-400">{(run.pass_rate * 100).toFixed(0)}%</div>
                      <div className="text-xs text-[var(--color-text-muted)]">通过率</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-purple-400">{run.average_score.toFixed(2)}</div>
                      <div className="text-xs text-[var(--color-text-muted)]">平均分</div>
                  </div>
                </div>
                {run.results && (
                  <div className="space-y-1 mt-2">
                    {run.results.map((r) => (
                      <div key={r.case_id} className="flex items-center gap-2 text-xs">
                        <span className={r.passed ? 'text-green-400' : 'text-red-400'}>
                           {r.passed ? '通过' : '失败'}
                        </span>
                         <span className="text-[var(--color-text-muted)]">{r.case_id}</span>
                         <span className="text-[var(--color-text-muted)]">{r.score.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
