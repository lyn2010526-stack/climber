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

interface EvalAgent {
  id: string;
  name: string;
}

export function EvalDashboard() {
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [agents, setAgents] = useState<EvalAgent[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState<string>('');

  const fetchDatasets = useCallback(async () => {
    try {
      const data = await api.listEvalDatasets();
      setDatasets(data);
    } catch {
      // ignore
    }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await api.listAgents();
      setAgents(data);
      if (data.length > 0) setSelectedAgent(current => current || data[0].id);
    } catch {
      // ignore
    }
  }, []);

  const runEval = async () => {
    if (!selectedDataset || !selectedAgent) {
      setError('请选择数据集和智能体');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api.runEvaluation(selectedDataset, selectedAgent);
      setRuns(current => [result, ...current]);
    } catch {
      setError('Network error');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDatasets();
    fetchAgents();
  }, [fetchAgents, fetchDatasets]);

  return (
    <div className="p-6 bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] min-h-full">
      <div className="flex items-center justify-between mb-6">
         <h2 className="text-xl font-bold">评估仪表板</h2>
      </div>

      {error && <div className="text-red-400 text-sm mb-4">{error}</div>}

      {/* Datasets */}
      <div className="mb-6">
           <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">数据集</h3>
         {datasets.length === 0 ? (
            <div className="text-[var(--color-text-muted)] text-sm">暂无数据集</div>
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

      <div className="mb-6">
        <h3 className="text-sm font-semibold text-[var(--color-text-muted)] mb-2">智能体</h3>
        <select
          value={selectedAgent}
          onChange={(event) => setSelectedAgent(event.target.value)}
          className="w-full max-w-sm px-3 py-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] text-sm"
        >
          <option value="">请选择智能体</option>
          {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
        </select>
      </div>

      {/* Run button */}
      {selectedDataset && selectedAgent && (
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

export default EvalDashboard;
