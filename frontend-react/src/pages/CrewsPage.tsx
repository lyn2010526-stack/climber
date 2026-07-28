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
    await api.updateCrew?.(selectedCrew.id, { agents: updated });
    setMemberForm({ agent_id: '', role: 'executor', model_provider: '', model_id: '' });
    setShowMemberForm(false);
    setSelectedCrew({ ...selectedCrew, agents: updated });
  };

  const removeMember = async (index: number) => {
    if (!selectedCrew) return;
    const updated = members.filter((_, i) => i !== index);
    setMembers(updated);
    await api.updateCrew?.(selectedCrew.id, { agents: updated });
    setSelectedCrew({ ...selectedCrew, agents: updated });
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold">团队管理</h2>
            <p className="text-gray-400 text-sm mt-1">多智能体协作</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-600-hover text-white rounded-lg text-sm font-medium transition-colors"
          >
             <Plus size={16} /> 新建团队
          </button>
        </div>

        {showForm && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
            <div className="grid gap-4">
              <input
                placeholder="团队名称"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-100"
              />
              <input
                placeholder="描述"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-100"
              />
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={createCrew}
                disabled={!form.name}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-600-hover text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                 创建团队
              </button>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-400 flex-1">{error}</p>
            <button
              onClick={loadCrews}
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
                    <div className="h-3 w-48 bg-gray-700 rounded" />
                  </div>
                  <div className="h-8 w-20 bg-gray-700 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Crew list */}
        {!loading && !error && (
          <div className="space-y-3">
            {crews.map(crew => (
              <div key={crew.id} className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                    <Users size={20} className="text-green-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium">{crew.name}</h3>
                     <p className="text-sm text-gray-400">{crew.description || '暂无描述'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openCrewDetail(crew)}
                      className="flex items-center gap-1 px-3 py-2 text-xs text-gray-400 hover:text-gray-200 bg-gray-700 rounded-lg transition-colors"
                    >
                      <Users size={14} />
                      管理成员
                    </button>
                    <button
                      onClick={() => runCrew(crew.id)}
                      disabled={running === crew.id}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-600-hover text-white rounded-lg text-sm disabled:opacity-50"
                    >
                       <Play size={14} /> {running === crew.id ? '运行中...' : '运行'}
                    </button>
                  </div>
                </div>
                {results[crew.id] && (
                  <div className="mt-3">
                    <pre className="code-block text-xs">
                      {JSON.stringify(results[crew.id], null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
            {crews.length === 0 && (
              <div className="text-center py-16 text-gray-400">
                <Users size={48} className="mx-auto mb-4 opacity-30" />
                 <p>暂无团队。创建一个多智能体团队开始使用。</p>
              </div>
            )}
          </div>
        )}

        {/* Crew Detail Panel */}
        {selectedCrew && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedCrew(null)}>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium">{selectedCrew.name} - 成员管理</h3>
                <button onClick={() => setSelectedCrew(null)} className="text-gray-400 hover:text-gray-200">关闭</button>
              </div>

              {/* Add Member */}
              {showMemberForm ? (
                <div className="p-3 bg-gray-700/50 rounded-lg space-y-2 mb-4">
                  <input
                    type="text"
                    value={memberForm.agent_id}
                    onChange={(e) => setMemberForm({ ...memberForm, agent_id: e.target.value })}
                    placeholder="Agent ID"
                    className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-200"
                  />
                  <select
                    value={memberForm.role}
                    onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                    className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-200"
                  >
                    <option value="planner">Planner</option>
                    <option value="researcher">Researcher</option>
                    <option value="executor">Executor</option>
                    <option value="auditor">Auditor</option>
                    <option value="participant">Participant</option>
                    <option value="observer">Observer</option>
                  </select>
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setShowMemberForm(false)} className="px-2 py-1 text-xs text-gray-500">取消</button>
                    <button onClick={addMember} disabled={!memberForm.agent_id.trim()} className="px-2 py-1 text-xs bg-blue-600 text-white rounded disabled:opacity-50">添加</button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setShowMemberForm(true)} className="flex items-center gap-1 px-3 py-1.5 text-xs text-blue-400 hover:text-blue-300 mb-4">
                  <Plus size={12} /> 添加成员
                </button>
              )}

              {/* Members List */}
              <div className="space-y-2">
                {members.map((member, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-700/30 rounded-lg">
                    <div>
                      <span className="text-xs text-gray-200">{member.agent_id}</span>
                      <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">{member.role}</span>
                    </div>
                    <button onClick={() => removeMember(index)} className="text-[10px] text-red-400 hover:text-red-300">移除</button>
                  </div>
                ))}
                {members.length === 0 && <p className="text-xs text-gray-500 text-center py-2">暂无成员</p>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
