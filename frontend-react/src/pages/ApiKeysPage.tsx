import { useState, useEffect } from 'react';
import { Plus, Trash2, Key } from 'lucide-react';
import { api } from '../api';

const PROVIDERS = ['openai', 'anthropic', 'google', 'ollama', 'stepfun'];

export function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: 'openai', name: '', api_key: '', base_url: '' });


  useEffect(() => { loadKeys(); }, []);

  const loadKeys = () => {
    api.listApiKeys().then(setKeys).catch(() => {});
  };

  const addKey = async () => {
    await api.addApiKey(form);
    setShowForm(false);
    setForm({ provider: 'openai', name: '', api_key: '', base_url: '' });
    loadKeys();
  };

  const deleteKey = async (id: string) => {
    await api.deleteApiKey(id);
    loadKeys();
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white">API 密钥</h2>
            <p className="text-gray-400 text-sm mt-1.5">管理模型提供商凭据</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-blue-500/20 active:scale-[0.97]"
          >
             <Plus size={16} /> 添加密钥
          </button>
        </div>

        {showForm && (
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-3xl p-6 mb-6 backdrop-blur-sm">
            <div className="grid grid-cols-2 gap-4">
              <select
                value={form.provider}
                onChange={(e) => setForm({ ...form, provider: e.target.value })}
                className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
              >
                {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <input
                placeholder="名称（例如：个人 GPT-4）"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
              />
              <input
                placeholder="API 密钥"
                type="password"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                className="col-span-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
              />
              <input
                placeholder="Base URL（可选，自托管时使用）"
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                className="col-span-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
              />
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={addKey}
                disabled={!form.name || !form.api_key}
                className="px-6 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold disabled:opacity-40 transition-all duration-200 active:scale-[0.97] shadow-lg shadow-blue-500/20"
              >
                 保存密钥
              </button>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {keys.map(key => (
            <div
              key={key.id}
              className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 flex items-center gap-4 backdrop-blur-sm hover:border-[#007AFF]/30 transition-all duration-200"
            >
              <div className="w-10 h-10 rounded-2xl bg-amber-500/10 flex items-center justify-center">
                <Key size={20} className="text-amber-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-200">{key.name}</h3>
                <p className="text-sm text-gray-500">{key.provider}{key.base_url ? ` | ${key.base_url}` : ''}</p>
              </div>
              <button
                onClick={() => deleteKey(key.id)}
                className="p-2 hover:bg-red-500/10 rounded-xl text-gray-400 hover:text-red-400 transition-all duration-200"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {keys.length === 0 && (
            <div className="text-center py-16">
              <div className="w-16 h-16 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                <Key size={28} className="text-gray-600" />
              </div>
              <p className="text-gray-500 text-sm">暂无 API 密钥。添加一个以连接到模型提供商。</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
