import { useState, useEffect } from 'react';
import { Play, FileCode, RefreshCw, AlertCircle, Plus, Edit, List, GitBranch, CheckCircle2, XCircle } from 'lucide-react';
import { api } from '../api';
import { WorkflowEditor } from '../components/workflow/WorkflowEditor';
import type { Node, Edge } from '@xyflow/react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { SkeletonList } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

export function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});
  const [editingWorkflow, setEditingWorkflow] = useState<any>(null);
  const [showEditor, setShowEditor] = useState(false);

  useEffect(() => {
    loadWorkflows();
  }, []);

  const loadWorkflows = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listWorkflows();
      setWorkflows(data);
    } catch (e: any) {
      const detail = e.message && e.message !== 'Request failed' ? ` ${e.message}` : '';
      setError(`Unable to reach the workflow service. Check that the API is running, then retry.${detail}`);
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

  const openNewEditor = () => {
    setEditingWorkflow(null);
    setShowEditor(true);
  };

  const openEditEditor = (wf: any) => {
    setEditingWorkflow(wf);
    setShowEditor(true);
  };

  const handleEditorSave = (_payload: { id: string; nodes: Node[]; edges: Edge[] }) => {
    loadWorkflows();
    setEditingWorkflow(null);
    setShowEditor(false);
  };

  const handleEditorRun = ({ id, result }: { id: string; result: any }) => {
    setResults(prev => ({ ...prev, [id]: result }));
  };

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title="Workflows"
          description="DAG-based workflow automation"
          icon={<FileCode size={20} className="text-[var(--color-accent)]" />}
          actions={
            <Button variant="primary" size="sm" icon={<Plus size={14} />} onClick={openNewEditor}>
              New Workflow
            </Button>
          }
        />

        <div className="mt-4 flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-3 md:mt-6">
          <div className="flex items-center gap-1" role="tablist" aria-label="工作流视图">
            <button role="tab" aria-selected="true" className="view-tab is-active"><List size={14} />列表</button>
            <button role="tab" aria-selected="false" className="view-tab" onClick={openNewEditor}><GitBranch size={14} />画布</button>
          </div>
          {!loading && !error && <p className="text-xs text-[var(--color-text-muted)]">{workflows.length} workflows</p>}
        </div>

        <div className="mt-3">
          {error && (
            <Card variant="default" className="border-[var(--color-error)]/30" role="alert">
              <CardContent className="p-3 md:p-4 flex items-center gap-3">
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
                <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
                <Button variant="outline" size="sm" onClick={loadWorkflows} icon={<RefreshCw size={14} />}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          )}

          {loading && <SkeletonList count={3} />}

          {!loading && !error && workflows.length === 0 && (
            <EmptyState
              icon="file"
              title="No workflows"
              description="Create your first workflow from a template"
              action={
                <Button variant="primary" size="sm" onClick={openNewEditor} icon={<Plus size={14} />}>
                  Create Workflow
                </Button>
              }
            />
          )}

          {!loading && !error && workflows.length > 0 && (
            <div className="grid gap-2" aria-live="polite">
              {workflows.map(wf => (
                <Card key={wf.id} variant="default">
                  <CardContent className="p-4 md:p-5">
                    <div className="flex flex-wrap items-center gap-3 md:gap-4">
                      <div className="h-9 w-9 md:h-10 md:w-10 rounded-[var(--radius-md)] bg-[var(--color-accent-muted)] flex items-center justify-center ring-1 ring-[var(--color-accent)]/20 shrink-0">
                        <FileCode size={18} className="text-[var(--color-accent)]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm text-[var(--color-text-primary)] truncate">{wf.name}</h3>
                        <p className="mt-1 flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
                          <span>{Array.isArray(wf.nodes) ? wf.nodes.length : 0} nodes</span>
                          <span>{Array.isArray(wf.edges) ? wf.edges.length : 0} connections</span>
                          {wf.status && <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />{wf.status}</span>}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        icon={<Edit size={14} />}
                        onClick={() => openEditEditor(wf)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        icon={<Play size={14} />}
                        onClick={() => runWorkflow(wf.id)}
                        disabled={running === wf.id}
                        loading={running === wf.id}
                      >
                        Run
                      </Button>
                    </div>
                    {results[wf.id] && (
                      <div className="mt-3 border-t border-[var(--color-border-subtle)] pt-3">
                        <p className="mb-2 flex items-center gap-2 text-xs font-medium text-[var(--color-text-secondary)]">
                          {results[wf.id].error ? <XCircle size={14} className="text-[var(--color-error)]" /> : <CheckCircle2 size={14} className="text-[var(--color-success)]" />}
                          最近运行 {results[wf.id].error ? '失败' : '完成'}
                        </p>
                        <pre className="text-xs text-[var(--color-text-secondary)] bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-[var(--radius-md)] p-3 md:p-4 overflow-auto max-h-48 font-mono leading-relaxed">
                          {JSON.stringify(results[wf.id], null, 2)}
                        </pre>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {(editingWorkflow || showEditor) && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-2 backdrop-blur-sm md:p-8"
            role="dialog"
            aria-modal="true"
            aria-label={editingWorkflow ? 'Edit Workflow' : 'New Workflow'}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                setEditingWorkflow(null);
                setShowEditor(false);
              }
            }}
          >
            <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-[var(--radius-xl)] w-full h-full max-w-7xl max-h-[90vh] flex flex-col shadow-[var(--shadow-xl)]">
              <div className="flex items-center justify-between p-4 border-b border-[var(--color-border-subtle)] shrink-0">
                <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                  {editingWorkflow ? 'Edit Workflow' : 'New Workflow'}
                </h3>
                <Button
                  autoFocus
                  variant="ghost"
                  size="sm"
                  onClick={() => { setEditingWorkflow(null); setShowEditor(false); }}
                >
                  Close
                </Button>
              </div>
              <div className="flex-1 min-h-0">
                <WorkflowEditor
                  workflowId={editingWorkflow?.id}
                  initialNodes={editingWorkflow?.nodes || []}
                  initialEdges={editingWorkflow?.edges || []}
                  onSave={handleEditorSave}
                  onRun={handleEditorRun}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
