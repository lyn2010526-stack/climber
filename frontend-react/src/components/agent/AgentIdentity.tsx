import React, { useState } from 'react';
import {
  Bot, Edit3, Save, X, Target,
  Brain, Globe,
  Check,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface Agent {
  id: string;
  name: string;
  avatar: string;
  persona: string;
  goals: string[];
  preferences: string[];
  memoryScope: string;
  color: string;
}

const mockAgents: Agent[] = [
  {
    id: '1',
    name: '代码助手',
    avatar: 'CE',
    persona: '专业的软件工程师，擅长编写高质量代码，遵循最佳实践和设计模式。',
    goals: ['帮助开发者编写高质量代码', '自动化重复任务', '提供技术指导'],
    preferences: ['使用 TypeScript', '遵循项目规范', '优先简洁实现'],
    memoryScope: 'project',
    color: 'from-blue-500 to-cyan-400',
  },
  {
    id: '2',
    name: '架构顾问',
    avatar: 'AC',
    persona: '资深系统架构师，专注于系统设计、技术选型和性能优化。',
    goals: ['设计可扩展的系统架构', '优化性能瓶颈', '确保系统可靠性'],
    preferences: ['优先考虑可维护性', '遵循 SOLID 原则', '文档驱动'],
    memoryScope: 'global',
    color: 'from-violet-500 to-purple-400',
  },
];

const memoryScopes = [
  { id: 'project', label: '项目级', description: '记忆仅限当前项目' },
  { id: 'global', label: '全局', description: '记忆跨项目共享' },
  { id: 'session', label: '会话级', description: '记忆仅限当前会话' },
];

export function AgentIdentity() {
  const [agents, setAgents] = useState(mockAgents);
  const [activeAgentId, setActiveAgentId] = useState('1');
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState<Partial<Agent>>({});

  const activeAgent = agents.find(a => a.id === activeAgentId) || agents[0];

  const startEdit = () => {
    setEditData({ ...activeAgent });
    setEditing(true);
  };

  const saveEdit = () => {
    setAgents(prev => prev.map(a =>
      a.id === activeAgentId ? { ...a, ...editData } : a
    ));
    setEditing(false);
  };

  const addGoal = () => {
    setEditData(d => ({ ...d, goals: [...(d.goals || []), ''] }));
  };

  const updateGoal = (index: number, value: string) => {
    setEditData(d => ({
      ...d,
      goals: d.goals?.map((g, i) => i === index ? value : g) || [],
    }));
  };

  const removeGoal = (index: number) => {
    setEditData(d => ({
      ...d,
      goals: d.goals?.filter((_, i) => i !== index) || [],
    }));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-xl bg-gradient-to-br from-pink-500 to-rose-500 shadow-lg shadow-pink-500/20">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">智能体身份</h1>
            <p className="text-xs text-gray-500 mt-0.5">管理智能体人格、目标和偏好</p>
          </div>
        </div>

        {/* Agent selector */}
        <div className="flex items-center gap-2 mb-4">
          {agents.map(agent => (
            <button
              key={agent.id}
              onClick={() => setActiveAgentId(agent.id)}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-xl border transition-all',
                activeAgentId === agent.id
                  ? 'border-blue-500/30 bg-blue-500/[0.06]'
                  : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.1]'
              )}
            >
              <div className={cn(
                'w-6 h-6 rounded-lg bg-gradient-to-br flex items-center justify-center text-[10px] font-bold text-white',
                agent.color
              )}>
                {agent.avatar}
              </div>
              <span className={cn(
                'text-xs font-medium',
                activeAgentId === agent.id ? 'text-white' : 'text-gray-400'
              )}>
                {agent.name}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {/* Identity card */}
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
          {/* Banner */}
          <div className={cn('h-20 bg-gradient-to-r', activeAgent.color, 'opacity-20')} />

          <div className="p-5 -mt-8">
            <div className="flex items-end justify-between mb-5">
              <div className="flex items-end gap-4">
                <div className={cn(
                  'w-16 h-16 rounded-2xl bg-gradient-to-br flex items-center justify-center text-xl font-bold text-white shadow-lg',
                  activeAgent.color
                )}>
                  {activeAgent.avatar}
                </div>
                <div className="pb-1">
                  <h3 className="text-lg font-bold text-white">{activeAgent.name}</h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">ID: {activeAgent.id}</p>
                </div>
              </div>
              {!editing ? (
                <button
                  onClick={startEdit}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.06] border border-white/[0.08] text-gray-300 text-xs font-medium hover:bg-white/[0.1] transition-all"
                >
                  <Edit3 size={13} />
                  编辑
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditing(false)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.06] border border-white/[0.08] text-gray-300 text-xs font-medium hover:bg-white/[0.1] transition-all"
                  >
                    <X size={13} />
                    取消
                  </button>
                  <button
                    onClick={saveEdit}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 text-white text-xs font-medium shadow-lg shadow-blue-500/20 hover:brightness-110 transition-all"
                  >
                    <Save size={13} />
                    保存
                  </button>
                </div>
              )}
            </div>

            {/* Persona */}
            <div className="mb-5">
              <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">人格设定</label>
              {editing ? (
                <textarea
                  value={editData.persona || ''}
                  onChange={e => setEditData(d => ({ ...d, persona: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 focus:outline-none focus:border-blue-500/40 transition-all resize-none"
                />
              ) : (
                <p className="text-sm text-gray-300 leading-relaxed">{activeAgent.persona}</p>
              )}
            </div>

            {/* Goals */}
            <div className="mb-5">
              <div className="flex items-center justify-between mb-2">
                <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">目标</label>
                {editing && (
                  <button onClick={addGoal} className="text-[11px] text-blue-400 hover:text-blue-300 transition-colors">
                    + 添加
                  </button>
                )}
              </div>
              <div className="space-y-2">
                {(editing ? editData.goals : activeAgent.goals)?.map((goal, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Target size={12} className="text-amber-400 flex-shrink-0" />
                    {editing ? (
                      <>
                        <input
                          type="text"
                          value={goal}
                          onChange={e => updateGoal(i, e.target.value)}
                          className="flex-1 h-8 px-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs text-gray-200 focus:outline-none focus:border-blue-500/40 transition-all"
                        />
                        <button
                          onClick={() => removeGoal(i)}
                          className="p-1 rounded-lg text-gray-500 hover:text-red-400 transition-colors"
                        >
                          <X size={12} />
                        </button>
                      </>
                    ) : (
                      <span className="text-xs text-gray-300">{goal}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Memory scope */}
            <div>
              <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">记忆范围</label>
              {editing ? (
                <div className="space-y-2">
                  {memoryScopes.map(scope => (
                    <button
                      key={scope.id}
                      onClick={() => setEditData(d => ({ ...d, memoryScope: scope.id }))}
                      className={cn(
                        'w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left',
                        editData.memoryScope === scope.id
                          ? 'border-blue-500/30 bg-blue-500/[0.06]'
                          : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.1]'
                      )}
                    >
                      <Brain size={14} className={editData.memoryScope === scope.id ? 'text-blue-400' : 'text-gray-500'} />
                      <div className="flex-1">
                        <div className="text-xs font-medium text-white">{scope.label}</div>
                        <div className="text-[10px] text-gray-500">{scope.description}</div>
                      </div>
                      {editData.memoryScope === scope.id && <Check size={14} className="text-blue-400" />}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <Globe size={14} className="text-gray-500" />
                  <span className="text-xs text-gray-300">
                    {memoryScopes.find(s => s.id === activeAgent.memoryScope)?.label || activeAgent.memoryScope}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
