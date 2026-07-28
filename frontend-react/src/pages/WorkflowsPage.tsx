import { useState, useEffect } from 'react';
import { Play, FileCode, Layout, RefreshCw, AlertCircle, Plus, Edit } from 'lucide-react';
import { api } from '../api';
import { WorkflowEditor } from '../components/workflow/WorkflowEditor';
import type { Node, Edge } from '@xyflow/react';

export function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});
  const [editingWorkflow, setEditingWorkflow] = useState<any>(null);
  const [showEditor, setShowEditor] = useState(false);

  useEffect(() => {
    loadWorkflows();
    api.listWorkflowTemplates().then(setTemplates).catch(() => {});
  }, []);

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
      await api.createFromTemplate(templateId, {
        provider: 'openai',
        model_id: 'gpt-4o',
        api_key: 'placeholder',
      });
      loadWorkflows();
      setShowTemplates(false);
    } catch (e: any) {
      alert(`失败：${e.message}`);
    }
  };

  const openNewEditor = () => {
    setEditingWorkflow(null);
  };

  const openEditEditor = (wf: any) => {
    setEditingWorkflow(wf);
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
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
             <h2 className="text-2xl font-bold">工作流</h2>
             <p className="text-gray-400 text-sm mt-1">基于 DAG 的工作流自动化</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={openNewEditor}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-600-hover text-white rounded-lg text-sm transition-colors"
            >
              <Plus size={16} /> 新建工作流
            </button>
            <button
              onClick={() => setShowTemplates(!showTemplates)}
              className="flex items-center gap-2 px-4 py-2.5 bg-gray-700 border border-gray-700 hover:border-blue-500 text-gray-100 rounded-lg text-sm transition-colors"
            >
              <Layout size={16} /> 模板
            </button>
          </div>
        </div>

        {showTemplates && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
             <h3 className="font-medium mb-4">工作流模板</h3>
            <div className="grid grid-cols-2 gap-3">
              {templates.map(t => (
                <button
                  key={t.id}
                  onClick={() => applyTemplate(t.template_id)}
                  className="text-left p-4 bg-gray-700 border border-gray-700 rounded-lg hover:border-blue-500 transition-colors"
                >
                  <div className="font-medium text-sm">{t.name}</div>
                  <div className="text-xs text-gray-400 mt-1">{t.description}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {(editingWorkflow || showEditor) && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-8">
            <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full h-full max-w-7xl max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between p-4 border-b border-gray-700">
                <h3 className="text-lg font-semibold text-white">
                  {editingWorkflow ? '编辑工作流' : '新建工作流'}
                </h3>
                <button
                  onClick={() => { setEditingWorkflow(null); setShowEditor(false); }}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  关闭
                </button>
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

        {/* Error state */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-400 flex-1">{error}</p>
            <button
              onClick={loadWorkflows}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
            >
              <RefreshCw size={14} /> 重试
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-5 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-gray-700" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 bg-gray-700 rounded" />
                    <div className="h-3 w-24 bg-gray-700 rounded" />
                  </div>
                  <div className="h-8 w-20 bg-gray-700 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Workflow list */}
        {!loading && !error && (
          <div className="space-y-3">
            {workflows.map(wf => (
              <div
                key={wf.id}
                className="bg-gray-800 border border-gray-700 rounded-xl p-5"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <FileCode size={20} className="text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium">{wf.name}</h3>
                    <p className="text-sm text-gray-400">{Array.isArray(wf.nodes) ? wf.nodes.length : 0} nodes</p>
                  </div>
                  <button
                    onClick={() => openEditEditor(wf)}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded-lg text-sm transition-colors"
                  >
                    <Edit size={14} /> 编辑
                  </button>
                  <button
                    onClick={() => runWorkflow(wf.id)}
                    disabled={running === wf.id}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-600-hover text-white rounded-lg text-sm disabled:opacity-50"
                  >
                     <Play size={14} /> {running === wf.id ? '运行中...' : '运行'}
                  </button>
                </div>
                {results[wf.id] && (
                  <div className="mt-3">
                    <pre className="code-block text-xs">
                      {JSON.stringify(results[wf.id], null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
            {workflows.length === 0 && !showTemplates && (
              <div className="text-center py-16 text-gray-400">
                <FileCode size={48} className="mx-auto mb-4 opacity-30" />
                 <p>暂无工作流。使用模板开始创建。</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
