import { Brain, Sliders, Zap, Timer, Shield } from 'lucide-react';
import { Section } from './Section';

export function ConfigPanel({ session }: { session: any }) {
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
