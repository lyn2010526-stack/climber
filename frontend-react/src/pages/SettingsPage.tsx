import { useState } from 'react';
import { Settings, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import { ToggleSwitch } from '../components/settings/ToggleSwitch';
import { useAgentMode } from '../hooks/useAgentMode';
import { cn } from '../lib/utils';

const MODE_DESCRIPTIONS: Record<string, { title: string; description: string }> = {
  'off-off': {
    title: '普通对话模式',
    description: '基础对话模式，不加载高级Agent提示词，不启动代码检索MCP，适合简单问答场景。',
  },
  'on-off': {
    title: '自治智能体模式',
    description: '加载高级自主Agent提示词，解锁任务拆解、自动规划、持续执行、结果自省复盘能力。',
  },
  'off-on': {
    title: 'Token节流代码检索模式',
    description: '启动jCodeMunch代码检索服务，强制AI优先检索代码片段，减少无效Token消耗。',
  },
  'on-on': {
    title: '全功能模式',
    description: '高级自主Agent + 代码检索节流，最大化智能与效率，适合复杂项目开发场景。',
  },
};

function McpStatusBadge({ status }: { status: string }) {
  const config = {
    disconnected: { icon: XCircle, color: 'text-gray-400', label: '未连接' },
    starting: { icon: AlertCircle, color: 'text-yellow-400', label: '启动中' },
    ready: { icon: CheckCircle2, color: 'text-green-400', label: '就绪' },
    error: { icon: XCircle, color: 'text-red-400', label: '失败' },
    restarting: { icon: AlertCircle, color: 'text-yellow-400', label: '重启中' },
  };

  const { icon: Icon, color, label } = config[status as keyof typeof config] || config.disconnected;

  return (
    <div className={cn('flex items-center gap-1.5', color)}>
      <Icon size={14} />
      <span className="text-xs">{label}</span>
    </div>
  );
}

export function SettingsPage() {
  const { mode, loading, error, toggleAutonomous, toggleMcp, refresh } = useAgentMode();
  const [mcpError, setMcpError] = useState<string | null>(null);

  const modeKey = `${mode.autonomous_agent_mode ? 'on' : 'off'}-${mode.token_throttle_mcp_enabled ? 'on' : 'off'}`;

  const handleMcpToggle = async () => {
    const newValue = !mode.token_throttle_mcp_enabled;
    await toggleMcp();

    if (newValue) {
      setMcpError(null);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await refresh();

      if (mode.mcp_status === 'error') {
        setMcpError('代码检索服务启动失败，对话功能仍可使用，代码检索能力暂时不可用');
      }
    } else {
      setMcpError(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400 text-sm">加载设置中...</div>
      </div>
    );
  }

  const currentMode = MODE_DESCRIPTIONS[modeKey as keyof typeof MODE_DESCRIPTIONS] ?? MODE_DESCRIPTIONS['off-off'];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
          <Settings size={20} className="text-gray-400" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-white">设置</h1>
          <p className="text-sm text-gray-400">管理 Agent 模式与 MCP 服务</p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <ToggleSwitch
          label="自治智能体模式"
          description="加载高级自主Agent提示词，解锁任务拆解、自动规划、持续执行、结果自省复盘能力。关闭则切换普通对话模式，不依赖任何MCP，可独立运行。"
          checked={mode.autonomous_agent_mode}
          onChange={toggleAutonomous}
        />

        <ToggleSwitch
          label="Token 节流｜代码定向检索 MCP"
          description="启动 jCodeMunch 索引服务，动态追加一段附加约束提示；强制AI优先检索代码片段，禁止一次性读取完整项目文件夹，减少无效Token消耗。关闭则断开MCP并移除约束规则。"
          checked={mode.token_throttle_mcp_enabled}
          onChange={handleMcpToggle}
          status={mode.mcp_status as 'idle' | 'starting' | 'ready' | 'error'}
        />

        {mode.token_throttle_mcp_enabled && (
          <div className="px-5 py-3 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">MCP 服务状态</span>
              <McpStatusBadge status={mode.mcp_status} />
            </div>
          </div>
        )}
      </div>

      {mcpError && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle size={20} className="text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-400 mb-1">
                代码检索服务启动失败
              </h3>
              <p className="text-xs text-red-300/80 leading-relaxed">
                {mcpError}
              </p>
              <button
                onClick={() => setMcpError(null)}
                className="mt-3 px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 text-xs transition-colors"
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="p-5 rounded-2xl border border-white/10 bg-white/[0.02]">
        <h3 className="text-sm font-semibold text-white mb-3">当前运行模式</h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">{currentMode?.title}</span>
            <span className="text-xs text-gray-500">
              {mode.autonomous_agent_mode ? '自治智能体' : '普通对话'} + {mode.token_throttle_mcp_enabled ? 'MCP节流' : '无MCP'}
            </span>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">
            {currentMode?.description}
          </p>
        </div>
      </div>
    </div>
  );
}
