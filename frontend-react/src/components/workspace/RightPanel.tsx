import { useState, useEffect } from 'react';
import {
  Settings, GitBranch, Activity, FolderTree, ChevronDown, ChevronRight,
  Zap, Brain, Sliders, Timer, Shield, FileDiff, Wrench,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { ReasoningPanel } from './ReasoningPanel';
import { DiffPanel } from '../code/DiffPanel';
import { ToolCallVisualization } from '../agent/ToolCallVisualization';
import type { ToolCall } from '../agent/ToolCallVisualization';
import { api } from '../../api';

export function RightPanel() {
  const { rightPanelTab, setRightPanelTab, rightPanelOpen, activeSessionId, sessions } = useWorkspaceStore();

  if (!rightPanelOpen) return null;

  const activeSession = sessions.find(s => s.id === activeSessionId);

  const tabs = [
    { id: 'config' as const, icon: Settings, label: '配置' },
    { id: 'diff' as const, icon: FileDiff, label: 'Diff' },
    { id: 'toolcalls' as const, icon: Wrench, label: '工具' },
    { id: 'dag' as const, icon: GitBranch, label: 'DAG' },
    { id: 'trace' as const, icon: Activity, label: '链路' },
    { id: 'reasoning' as const, icon: Brain, label: '推理' },
    { id: 'files' as const, icon: FolderTree, label: '文件' },
  ];

  return (
    <div className="w-80 bg-[#0F0F14]/80 backdrop-blur-2xl border-l border-white/10 flex flex-col shadow-sm shadow-white/5">
      {/* Tab bar */}
      <div className="flex border-b border-white/10">
        {tabs.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setRightPanelTab(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all relative ${
              rightPanelTab === id
                ? 'text-white'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <Icon size={13} />
            <span>{label}</span>
            {rightPanelTab === id && (
              <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-[#007AFF] rounded-full shadow-sm shadow-blue-500/30" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-3">
        {rightPanelTab === 'config' && <ConfigPanel session={activeSession} />}
        {rightPanelTab === 'diff' && <DiffPanelTab sessionId={activeSessionId} />}
        {rightPanelTab === 'toolcalls' && <ToolCallsTab sessionId={activeSessionId} />}
        {rightPanelTab === 'dag' && <DAGPanel />}
        {rightPanelTab === 'trace' && <TracePanel />}
        {rightPanelTab === 'reasoning' && <ReasoningPanel />}
        {rightPanelTab === 'files' && <FilesPanel />}
      </div>
    </div>
  );
}

// ── Config Panel ──

function ConfigPanel({ session }: { session: any }) {
  const provider = session?.modelConfig?.provider || '—';
  const modelId = session?.modelConfig?.modelId || '—';
  const temperature = session?.modelConfig?.temperature ?? 0.7;

  return (
    <div className="space-y-3">
      {/* Model Config */}
      <Section title="模型配置" icon={Sliders}>
        <div className="space-y-2.5">
          <div className="flex justify-between text-xs">
            <span className="text-[var(--color-text-muted)]">提供商</span>
            <span className="text-[var(--color-text-secondary)] font-medium">{provider}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-[var(--color-text-muted)]">模型</span>
            <span className="text-[var(--color-text-secondary)] font-medium">{modelId}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-[var(--color-text-muted)]">温度</span>
            <span className="text-[var(--color-text-secondary)] font-medium">{temperature}</span>
          </div>
        </div>
      </Section>

      {/* Active Skills */}
      <Section title="已启用技能" icon={Brain}>
        <div className="flex flex-wrap gap-1.5">
          {(session?.activeSkills && session.activeSkills.length > 0)
            ? session.activeSkills.map((skill: string) => (
              <span key={skill} className="px-2.5 py-1 bg-purple-500/10 text-purple-400 rounded-xl text-xs font-medium">
                {skill}
              </span>
            ))
            : <span className="text-xs text-[var(--color-text-muted)]">暂无启用技能</span>
          }
        </div>
      </Section>

      {/* Active Tools */}
      <Section title="已启用工具" icon={Zap}>
        <div className="flex flex-wrap gap-1.5">
          {(session?.activeTools && session.activeTools.length > 0)
            ? session.activeTools.map((tool: string) => (
              <span key={tool} className="px-2.5 py-1 bg-white/5 text-[var(--color-text-secondary)] rounded-xl text-xs font-medium border border-white/10">
                {tool}
              </span>
            ))
            : <span className="text-xs text-[var(--color-text-muted)]">暂无启用工具</span>
          }
        </div>
      </Section>

      {/* Token Usage */}
      <Section title="Token 用量" icon={Timer}>
        <div className="space-y-2.5">
          <div className="flex justify-between text-xs">
            <span className="text-[var(--color-text-muted)]">已用</span>
            <span className="text-[var(--color-text-secondary)] font-medium">{session?.tokenUsage?.used || 0} / {session?.tokenUsage?.limit || 128000}</span>
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#007AFF] rounded-full transition-all"
              style={{ width: `${Math.min(((session?.tokenUsage?.used || 0) / (session?.tokenUsage?.limit || 128000)) * 100, 100)}%` }}
            />
          </div>
        </div>
      </Section>

      {/* Safety */}
      <Section title="安全设置" icon={Shield}>
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--color-text-secondary)]">沙箱模式</span>
            <span className="text-xs text-green-400 font-medium">运行中</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--color-text-secondary)]">会话状态</span>
            <span className="text-xs text-[var(--color-text-muted)]">{session?.status || '空闲'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--color-text-secondary)]">文件隔离</span>
            <span className="text-xs text-green-400 font-medium">仅项目内</span>
          </div>
        </div>
      </Section>
    </div>
  );
}

// ── DAG Panel ──

function DAGPanel() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      try {
        const data = await api.getClusterStatus();
          if (data.plan) {
            setNodes(data.plan.map((p: any) => ({
              id: p.id || String(Math.random()),
              label: p.description || p.task || 'Unknown',
              status: p.status || 'pending',
            })));
          }
      } catch { /* skip */ }
      setLoading(false);
    };
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-[var(--color-text-muted)]">正在加载工作流状态...</p>
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center gap-2 animate-pulse">
              <div className="w-3 h-3 rounded-full bg-white/10" />
              <div className="h-3 w-32 bg-white/5 rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-[var(--color-text-muted)]">任务依赖图</p>
        <div className="text-center py-8">
          <GitBranch size={24} className="mx-auto text-[var(--color-text-muted)]" />
           <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无活跃工作流</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Create a cluster to see the DAG</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
       <p className="text-xs text-[var(--color-text-muted)]">任务依赖图 — 根据需求自动规划</p>
      <div className="space-y-1">
        {nodes.map((node, i) => (
          <div key={node.id} className="flex items-center gap-2">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full border-2 ${
                node.status === 'completed' ? 'bg-green-500 border-green-500' :
                node.status === 'running' ? 'bg-[#007AFF] border-[#007AFF] animate-pulse' :
                'border-[var(--color-border-subtle)]'
              }`} />
              {i < nodes.length - 1 && <div className="w-0.5 h-4 bg-white/10" />}
            </div>
            <span className={`text-xs ${
              node.status === 'completed' ? 'text-green-400' :
              node.status === 'running' ? 'text-blue-400 font-medium' :
              'text-[var(--color-text-muted)]'
            }`}>
              {node.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Trace Panel ──

function TracePanel() {
  const [traces, setTraces] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchTraces = async () => {
      setLoading(true);
      try {
        const data = await api.listTraces();
          setTraces(data.traces || data || []);
      } catch { /* skip */ }
      setLoading(false);
    };
    fetchTraces();
  }, []);

  if (loading) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">加载追踪中...</p>
        <div className="space-y-1.5">
          {[1, 2].map(i => (
            <div key={i} className="p-2 bg-white/5 rounded-xl animate-pulse">
              <div className="h-3 w-24 bg-white/10 rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">完整执行追踪</p>
        <div className="text-center py-8">
          <Activity size={24} className="mx-auto text-[var(--color-text-muted)]" />
           <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无追踪数据</p>
           <p className="text-[10px] text-[var(--color-text-muted)] mt-1">运行一次会话即可查看执行追踪</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
       <p className="text-xs text-[var(--color-text-muted)]">完整执行追踪 — 包含每次 LLM 调用和工具调用</p>
      <div className="space-y-1.5">
        {traces.map(t => (
          <div key={t.id} className="p-2 bg-white/5 rounded-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`px-1.5 py-0.5 rounded-xl text-[10px] font-medium ${
                  t.type === 'LLM' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-400'
                }`}>
                  {t.type}
                </span>
                <span className="text-xs text-[var(--color-text-secondary)]">{t.label || t.name || 'Unknown'}</span>
              </div>
              <span className="text-[10px] text-[var(--color-text-muted)]">{t.time || ''}</span>
            </div>
            <div className="flex gap-3 mt-1 text-[10px] text-[var(--color-text-muted)]">
              <span>{t.duration || 0}ms</span>
               {(t.tokens || 0) > 0 && <span>{t.tokens} 令牌</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Files Panel ──

function FilesPanel() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDocuments = async () => {
      setLoading(true);
      try {
        const data = await api.listDocuments();
          setDocuments(data || []);
      } catch { /* skip */ }
      setLoading(false);
    };
    fetchDocuments();
  }, []);

  if (loading) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">加载文档中...</p>
        <div className="space-y-1">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-6 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">项目文件浏览器</p>
        <div className="text-center py-8">
          <FolderTree size={24} className="mx-auto text-[var(--color-text-muted)]" />
           <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无上传文档</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Upload documents to use with RAG</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
       <p className="text-xs text-[var(--color-text-muted)]">已上传文档 ({documents.length})</p>
      <div className="bg-white/5 rounded-2xl p-1.5 space-y-0.5 border border-white/10">
        {documents.map(doc => (
          <div key={doc.id} className="flex items-center gap-2 py-1.5 px-2 rounded-xl hover:bg-white/5 text-xs text-[var(--color-text-secondary)] transition-colors">
            <FolderTree size={12} className="text-[var(--color-text-muted)]" />
            <span className="truncate flex-1">{doc.filename || doc.name}</span>
            {doc.chunks && <span className="text-[10px] text-[var(--color-text-muted)]">{doc.chunks} chunks</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Diff Panel Tab ──

function DiffPanelTab({ sessionId }: { sessionId: string | null }) {
  const [diffText, setDiffText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    api.getSessionMessages(sessionId).then((messages) => {
      const toolResults = messages.filter((m: any) => m.type === 'tool-result');
      const diffMessages = toolResults.filter((m: any) =>
        m.content && typeof m.content === 'string' && m.content.includes('diff --git')
      );
      if (diffMessages.length > 0) {
        const latestDiff = diffMessages[diffMessages.length - 1];
        setDiffText(latestDiff.content);
      }
    }).catch(() => {})
    .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">加载变更中...</p>
        <div className="space-y-1.5">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-6 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!diffText) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">文件变更视图</p>
        <div className="text-center py-8">
          <FileDiff size={24} className="mx-auto text-[var(--color-text-muted)]" />
          <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无文件变更</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">执行文件操作后在此查看 diff</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--color-text-muted)]">文件变更 — 最新 diff</p>
      <DiffPanel diffText={diffText} />
    </div>
  );
}

// ── Tool Calls Tab ──

function ToolCallsTab({ sessionId }: { sessionId: string | null }) {
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    api.getSessionMessages(sessionId).then((messages) => {
      const toolMessages = messages.filter((m: any) => m.type === 'tool-call' || m.type === 'tool_call');
      const calls: ToolCall[] = toolMessages.map((m: any, idx: number) => ({
        id: m.id || `tool-${idx}`,
        name: m.metadata?.toolName || m.content?.name || 'unknown',
        arguments: m.metadata?.toolArgs || m.content?.arguments || {},
        result: m.content?.result,
        error: m.content?.error,
        status: m.metadata?.status || 'success',
        duration: m.metadata?.durationMs,
        startTime: m.timestamp,
      }));
      setToolCalls(calls);
    }).catch(() => {});
    setLoading(false);
  }, [sessionId]);

  if (loading) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">加载工具调用中...</p>
        <div className="space-y-1.5">
          {[1, 2].map(i => (
            <div key={i} className="p-2 bg-white/5 rounded-xl animate-pulse">
              <div className="h-3 w-24 bg-white/10 rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (toolCalls.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">工具调用记录</p>
        <div className="text-center py-8">
          <Wrench size={24} className="mx-auto text-[var(--color-text-muted)]" />
          <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无工具调用</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">智能体执行工具后在此查看</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--color-text-muted)]">工具调用 — 展开查看详情</p>
      <ToolCallVisualization calls={toolCalls} defaultExpanded={false} />
    </div>
  );
}

// ── Section Component ──

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl overflow-hidden backdrop-blur-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        <div className="p-1 rounded-lg bg-blue-500/10 text-blue-400">
          <Icon size={11} />
        </div>
        <span className="flex-1 text-left">{title}</span>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {expanded && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}
