import { useState } from 'react';
import { Lock, Edit3, Settings, Plus, Trash2, AlertTriangle } from 'lucide-react';

interface SkillMetadata {
  name: string;
  description: string;
  category: string;
  riskLevel: 'low' | 'high' | 'restricted';
  dependencies: string[];
  toolWhitelist: string[];
  toolBlacklist: string[];
  maxIterations: number;
  timeout: number;
  retryStrategy: 'auto' | 'stop' | 'ask';
  selfChecklist: string[];
  terminationCondition: string;
}

const defaultSkill: SkillMetadata = {
  name: '',
  description: '',
  category: 'engineering',
  riskLevel: 'low',
  dependencies: [],
  toolWhitelist: [],
  toolBlacklist: [],
  maxIterations: 20,
  timeout: 300,
  retryStrategy: 'auto',
  selfChecklist: [],
  terminationCondition: '',
};

export function SkillEditor() {
  const [skill, setSkill] = useState<SkillMetadata>(defaultSkill);
  const [promptText, setPromptText] = useState('');
  const [activeTab, setActiveTab] = useState<'prompt' | 'config' | 'checklist'>('prompt');

  return (
    <div className="h-full flex flex-col bg-[var(--color-bg-deep)]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-default)]">
        <div className="flex items-center gap-2">
          <Edit3 size={16} className="text-blue-400" />
           <h3 className="text-sm font-semibold">技能编辑器</h3>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1.5 text-xs bg-[var(--color-bg-surface-elevated)] text-[var(--color-text-secondary)] rounded-lg hover:bg-[var(--color-bg-surface-elevated)]/50">
            Import
          </button>
          <button className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Save
          </button>
        </div>
      </div>

      {/* L0 Read-only Section */}
      <div className="px-4 py-2 bg-[var(--color-bg-surface-1)] border-b border-[var(--color-border-default)]">
        <div className="flex items-center gap-2 mb-1">
          <Lock size={12} className="text-amber-400" />
          <span className="text-xs font-medium text-amber-400">L0 — Engine Base Rules (Read-Only)</span>
        </div>
        <p className="text-[10px] text-[var(--color-text-muted)] pl-5">
          Tool call format, anti-loop rules, safety locks — immutable engine directives
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[var(--color-border-default)]">
        {(['prompt', 'config', 'checklist'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium capitalize transition-colors relative ${
              activeTab === tab ? 'text-blue-400' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            {tab}
            {activeTab === tab && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'prompt' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-2">
              <Edit3 size={12} className="text-blue-400" />
              <span className="text-xs font-medium text-blue-400">L1 — Skill Instructions (Editable)</span>
            </div>
            <textarea
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
               placeholder="定义技能的行为、执行流程和工具使用规则..."
              className="w-full h-64 px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] resize-none focus:outline-none focus:border-blue-500/50 font-mono"
            />
            <div className="p-3 bg-[var(--color-bg-surface-elevated)] rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <Settings size={12} className="text-[var(--color-text-muted)]" />
                <span className="text-xs text-[var(--color-text-muted)]">动态注入预览</span>
              </div>
              <p className="text-[10px] text-[var(--color-text-muted)]">
                 工具列表、项目环境信息和会话上下文将在运行时自动附加。
              </p>
            </div>
          </div>
        )}

        {activeTab === 'config' && (
          <div className="space-y-4">
             <Field label="技能名称">
               <input
                 value={skill.name}
                 onChange={(e) => setSkill({ ...skill, name: e.target.value })}
                 className="w-full px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-blue-500/50"
                 placeholder="my_custom_skill（示例）"
               />
             </Field>

             <Field label="描述">
               <textarea
                 value={skill.description}
                 onChange={(e) => setSkill({ ...skill, description: e.target.value })}
                 className="w-full h-16 px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] resize-none focus:outline-none focus:border-blue-500/50"
                 placeholder="此技能的功能..."
               />
             </Field>

             <div className="grid grid-cols-2 gap-3">
               <Field label="分类">
                 <select
                   value={skill.category}
                   onChange={(e) => setSkill({ ...skill, category: e.target.value })}
                   className="w-full px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)]"
                 >
                   <option value="engineering">工程</option>
                   <option value="quality">质量</option>
                   <option value="knowledge">知识</option>
                   <option value="core">核心</option>
                 </select>
               </Field>

               <Field label="风险等级">
                 <select
                   value={skill.riskLevel}
                   onChange={(e) => setSkill({ ...skill, riskLevel: e.target.value as any })}
                   className="w-full px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)]"
                 >
                   <option value="low">低</option>
                   <option value="high">高</option>
                   <option value="restricted">受限</option>
                 </select>
               </Field>
             </div>

             <div className="grid grid-cols-2 gap-3">
               <Field label="最大迭代次数">
                 <input
                   type="number"
                   value={skill.maxIterations}
                   onChange={(e) => setSkill({ ...skill, maxIterations: parseInt(e.target.value) || 20 })}
                   className="w-full px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-blue-500/50"
                 />
               </Field>

               <Field label="超时（秒）">
                 <input
                   type="number"
                   value={skill.timeout}
                   onChange={(e) => setSkill({ ...skill, timeout: parseInt(e.target.value) || 300 })}
                   className="w-full px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-blue-500/50"
                 />
               </Field>
             </div>

             <Field label="重试策略">
               <select
                 value={skill.retryStrategy}
                 onChange={(e) => setSkill({ ...skill, retryStrategy: e.target.value as any })}
                 className="w-full px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)]"
               >
                 <option value="auto">自动重试</option>
                 <option value="stop">失败停止</option>
                 <option value="ask">询问用户</option>
               </select>
             </Field>

            {skill.riskLevel === 'restricted' && (
              <div className="p-3 bg-amber-500/10 border border-warning/30 rounded-lg flex items-center gap-2">
                <AlertTriangle size={14} className="text-amber-400" />
                 <span className="text-xs text-amber-400">
                   受限技能需要管理员解锁后才能启用
                 </span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'checklist' && (
          <div className="space-y-3">
             <p className="text-xs text-[var(--color-text-muted)]">任务完成前必须通过的自检项</p>
            {skill.selfChecklist.map((item, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  value={item}
                  onChange={(e) => {
                    const next = [...skill.selfChecklist];
                    next[i] = e.target.value;
                    setSkill({ ...skill, selfChecklist: next });
                  }}
                  className="flex-1 px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-blue-500/50"
                   placeholder={`检查项 ${i + 1}`}
                />
                <button
                  onClick={() => setSkill({ ...skill, selfChecklist: skill.selfChecklist.filter((_, idx) => idx !== i) })}
                  className="p-1.5 text-[var(--color-text-muted)] hover:text-red-400"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
            <button
              onClick={() => setSkill({ ...skill, selfChecklist: [...skill.selfChecklist, ''] })}
              className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-400"
            >
               <Plus size={12} /> 添加检查项
            </button>

            <div className="mt-4">
               <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">终止条件</label>
              <textarea
                value={skill.terminationCondition}
                onChange={(e) => setSkill({ ...skill, terminationCondition: e.target.value })}
                className="w-full h-16 px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-default)] rounded-lg text-xs text-[var(--color-text-primary)] resize-none focus:outline-none focus:border-blue-500/50"
                 placeholder="该技能在什么条件下认为任务已完成？"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">{label}</label>
      {children}
    </div>
  );
}
