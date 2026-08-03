import { useState, useEffect } from 'react';
import { Plus, Play, Users, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';

interface CrewMember {
  agent_id: string;
  role: string;
  model_provider?: string;
  model_id?: string;
}

export function CrewsPage() {
  const [crews, setCrews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', description: '' });
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});
  const [selectedCrew, setSelectedCrew] = useState<any | null>(null);
  const [members, setMembers] = useState<CrewMember[]>([]);
  const [showMemberForm, setShowMemberForm] = useState(false);
  const [memberForm, setMemberForm] = useState<CrewMember>({ agent_id: '', role: 'executor', model_provider: '', model_id: '' });

  useEffect(() => {
    loadCrews();
  }, []);

  const loadCrews = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listCrews();
      setCrews(data);
    } catch (e: any) {
      setError(e.message || '加载团队失败');
    }
    setLoading(false);
  };

  const createCrew = async () => {
    await api.createCrew({ name: form.name, description: form.description, roles: [] });
    setShowForm(false);
    setForm({ name: '', description: '' });
    loadCrews();
  };

  const runCrew = async (id: string) => {
    setRunning(id);
    try {
      const result = await api.runCrew(id, {});
      setResults(prev => ({ ...prev, [id]: result }));
    } catch (e: any) {
      setResults(prev => ({ ...prev, [id]: { error: e.message } }));
    }
    setRunning(null);
  };

  const openCrewDetail = async (crew: any) => {
    setSelectedCrew(crew);
    setMembers(crew.agents || []);
  };

  const addMember = async () => {
    if (!selectedCrew || !memberForm.agent_id.trim()) return;
    const updated = [...members, memberForm];
    setMembers(updated);
    setMemberForm({ agent_id: '', role: 'executor', model_provider: '', model_id: '' });
    setShowMemberForm(false);
    setSelectedCrew({ ...selectedCrew, agents: updated });
  };

  const removeMember = async (index: number) => {
    if (!selectedCrew) return;
    const updated = members.filter((_, i) => i !== index);
    setMembers(updated);
    setSelectedCrew({ ...selectedCrew, agents: updated });
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">团队管理</h2>
            <p className="text-[var(--color-text-secondary)] text-sm mt-1">多智能体协作</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
          >
             <Plus size={16} /> 新建团队
          </button>
        </div>

        {showForm && (
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-6 mb-6">
            <div className="grid gap-4">
              <input
                placeholder="团队名称"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)]"
              />
              <input
                placeholder="描述"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)]"
              />
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={createCrew}
                disabled={!form.name}
                className="px-6 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold disabled:opacity-50 transition-all duration-200 active:scale-[0.97]"
              >
                 创建团队
              </button>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            <button
              onClick={loadCrews}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-xl transition-colors"
            >
              <RefreshCw size={14} /> 重试
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-white/[0.03]" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 bg-white/[0.03] rounded-xl" />
                    <div className="h-3 w-48 bg-white/[0.03] rounded-xl" />
                  </div>
                  <div className="h-8 w-20 bg-white/[0.03] rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Crew list */}
        {!loading && !error && (
          <div className="space-y-3">
            {crews.map(crew => (
              <div key={crew.id} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-[var(--color-success)]/10 flex items-center justify-center border border-[var(--color-success)]/20">
                    <Users size={20} className="text-[var(--color-success)]" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-[var(--color-text-primary)]">{crew.name}</h3>
                     <p className="text-sm text-[var(--color-text-muted)]">{crew.description || '暂无描述'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openCrewDetail(crew)}
                      className="flex items-center gap-1 px-3 py-2 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-xl transition-all duration-200"
                    >
                      <Users size={14} />
                       管理成员
                    </button>
                    <button
                      onClick={() => runCrew(crew.id)}
                      disabled={running === crew.id}
                      className="flex items-center gap-2 px-4 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm disabled:opacity-50 transition-all duration-200 active:scale-[0.97]"
                    >
                       <Play size={14} /> {running === crew.id ? '运行中...' : '运行'}
                    </button>
                  </div>
                </div>
                {results[crew.id] && (
                  <div className="mt-3">
                    <pre className="code-block text-xs text-[var(--color-text-primary)]">
                      {JSON.stringify(results[crew.id], null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
            {crews.length === 0 && (
              <div className="text-center py-16 text-[var(--color-text-muted)]">
                <Users size={48} className="mx-auto mb-4 opacity-30" />
                 <p>暂无团队。创建一个多智能体团队开始使用。</p>
              </div>
            )}
          </div>
        )}

        {/* Crew Detail Panel */}
        {selectedCrew && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedCrew(null)}>
            <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-[var(--color-text-primary)]">{selectedCrew.name} - 成员管理</h3>
                <button onClick={() => setSelectedCrew(null)} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">关闭</button>
              </div>

              {/* Add Member */}
              {showMemberForm ? (
                <div className="p-3 bg-white/[0.02] border border-[var(--color-border-subtle)] rounded-xl space-y-2 mb-4">
                  <input
                    type="text"
                    value={memberForm.agent_id}
                    onChange={(e) => setMemberForm({ ...memberForm, agent_id: e.target.value })}
                    placeholder="Agent ID"
                    className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)]"
                  />
                  <select
                    value={memberForm.role}
                    onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                    className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)]"
                  >
                    <option value="planner">Planner</option>
                    <option value="researcher">Researcher</option>
                    <option value="executor">Executor</option>
                    <option value="auditor">Auditor</option>
                    <option value="participant">Participant</option>
                    <option value="observer">Observer</option>
                  </select>
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setShowMemberForm(false)} className="px-2 py-1 text-xs text-[var(--color-text-muted)]">取消</button>
                    <button onClick={addMember} disabled={!memberForm.agent_id.trim()} className="px-2 py-1 text-xs bg-[var(--color-accent)] text-white rounded-xl disabled:opacity-50 transition-all duration-200">添加</button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setShowMemberForm(true)} className="flex items-center gap-1 px-3 py-1.5 text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] mb-4 transition-colors">
                  <Plus size={12} /> 添加成员
                </button>
              )}

              {/* Members List */}
              <div className="space-y-2">
                {members.map((member, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-white/[0.02] border border-[var(--color-border-subtle)] rounded-xl">
                    <div>
                      <span className="text-xs text-[var(--color-text-primary)]">{member.agent_id}</span>
                      <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/20">{member.role}</span>
                    </div>
                    <button onClick={() => removeMember(index)} className="text-[10px] text-[var(--color-error)] hover:text-red-300 transition-colors">移除</button>
                  </div>
                ))}
                {members.length === 0 && <p className="text-xs text-[var(--color-text-muted)] text-center py-2">暂无成员</p>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
