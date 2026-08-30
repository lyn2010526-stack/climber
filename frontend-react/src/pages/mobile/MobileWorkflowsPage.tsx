import { useState, useEffect } from 'react';
import { Play, FileCode, RefreshCw, AlertCircle, Layout } from 'lucide-react';
import { api } from '../../api';

export function MobileWorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});

  useEffect(() => {
    loadWorkflows();
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await api.listWorkflowTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch { /* skip */ }
  };

  const loadWorkflows = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listWorkflows();
      setWorkflows(data);
    } catch (e: any) {
      setError(e.message || '加载工作流失败');
    }
    setLoading(false);
  };

  const runWorkflow = async (id: string) => {
    setRunning(id);
    try {
      const result = await api.runWorkflow(id, {});
      setResults(prev => ({ ...prev, [id]: result }));
    } catch (e: any) {
      setResults(prev => ({ ...prev, [id]: { error: e.message } }));
    }
    setRunning(null);
  };

  const applyTemplate = async (templateId: string) => {
    try {
      await api.createWorkflowFromTemplate(templateId);
      setShowTemplates(false);
      loadWorkflows();
    } catch (e: any) {
      setError(e.message || '应用模板失败');
    }
  };

  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
              工作流
            </h2>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
              基于 DAG 的工作流自动化
            </p>
          </div>
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="flex items-center gap-1.5 px-3 py-2.5 text-xs bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] rounded-2xl font-semibold transition-all duration-200 active:scale-[0.95]"
          >
            <Layout size={14} /> 模板
          </button>
        </div>

        {showTemplates && (
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">工作流模板</h3>
            <div className="space-y-2">
              {templates.map(t => (
                <button
                  key={t.template_id}
                  onClick={() => applyTemplate(t.template_id)}
                  className="w-full text-left p-3 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl active:border-[var(--color-accent)]/30 transition-all duration-200"
                >
                  <div className="text-sm font-medium text-[var(--color-text-primary)]">{t.name}</div>
                  <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">{t.description}</div>
                </button>
              ))}
              {templates.length === 0 && (
                <div className="text-center text-xs text-[var(--color-text-muted)] py-4">暂无可用模板</div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-3 mb-4 flex items-center gap-2.5">
            <AlertCircle size={16} className="text-[var(--color-error)] shrink-0" />
            <p className="text-xs text-[var(--color-error)] flex-1">{error}</p>
            <button
              onClick={loadWorkflows}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-[var(--color-error)] rounded-xl transition-colors"
            >
              <RefreshCw size={12} /> 重试
            </button>
          </div>
        )}

        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--color-bg-surface-2)]" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3.5 w-28 bg-[var(--color-bg-surface-2)] rounded-lg" />
                    <div className="h-3 w-20 bg-[var(--color-bg-surface-2)] rounded-lg" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && (
          <div className="space-y-3">
            {workflows.map(wf => (
              <div key={wf.id} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--color-accent-secondary)]/10 flex items-center justify-center border border-[var(--color-accent-secondary)]/20 shrink-0">
                    <FileCode size={16} className="text-[var(--color-accent-secondary)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-[var(--color-text-primary)] truncate">{wf.name}</h3>
                    <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                      {Array.isArray(wf.nodes) ? wf.nodes.length : 0} nodes
                    </p>
                  </div>
                  <button
                    onClick={() => runWorkflow(wf.id)}
                    disabled={running === wf.id}
                    className="flex items-center gap-1.5 px-3 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-xs font-semibold disabled:opacity-50 transition-all duration-200 active:scale-[0.95]"
                  >
                    <Play size={12} /> {running === wf.id ? '运行中...' : '运行'}
                  </button>
                </div>
                {results[wf.id] && (
                  <pre className="mt-3 text-[10px] text-[var(--color-text-primary)] bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl p-3 max-h-48 overflow-auto font-mono whitespace-pre-wrap break-all">
                    {JSON.stringify(results[wf.id], null, 2)}
                  </pre>
                )}
              </div>
            ))}
            {workflows.length === 0 && !showTemplates && (
              <div className="text-center py-12 text-[var(--color-text-muted)]">
                <FileCode size={40} className="mx-auto mb-3 opacity-30" />
                <p className="text-xs">暂无工作流。使用模板开始创建。</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
