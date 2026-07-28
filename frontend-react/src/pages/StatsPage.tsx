import { useState, useEffect } from 'react';
import { BarChart3, Bot, MessageSquare, Users, TrendingUp, Activity, Zap, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';

export function StatsPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (e: any) {
      setError(e.message || '加载统计信息失败');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-8">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
               <h2 className="text-2xl font-bold text-white">平台统计</h2>
               <p className="text-gray-400 text-sm mt-1.5">智能体平台运行概览</p>
            </div>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 animate-pulse">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-2xl bg-white/5" />
                  <div className="h-3 w-10 bg-white/5 rounded-xl" />
                </div>
                <div className="h-8 w-16 bg-white/5 rounded-xl" />
                <div className="h-3 w-20 bg-white/5 rounded-xl mt-1" />
              </div>
            ))}
          </div>
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 animate-pulse">
            <div className="h-4 w-28 bg-white/5 rounded-xl mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex items-center gap-3 py-2">
                  <div className="w-8 h-8 rounded-xl bg-white/5" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 w-32 bg-white/5 rounded-xl" />
                    <div className="h-2 w-20 bg-white/5 rounded-xl" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-3xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={28} className="text-red-400" />
          </div>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={loadStats}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const cards = [
    { label: 'Total Users', value: stats.total_users, icon: Users, color: 'text-blue-400', bg: 'bg-blue-900/20', trend: '+12%' },
    { label: 'Total Agents', value: stats.total_agents, icon: Bot, color: 'text-purple-400', bg: 'bg-purple-500/10', trend: '+5%' },
    { label: 'Total Sessions', value: stats.total_sessions, icon: MessageSquare, color: 'text-green-400', bg: 'bg-green-900/20', trend: '+24%' },
    { label: 'API Keys', value: stats.total_api_keys, icon: BarChart3, color: 'text-amber-400', bg: 'bg-amber-900/20', trend: '+3%' },
  ];

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white">平台统计</h2>
            <p className="text-gray-400 text-sm mt-1.5">智能体平台的实时概览</p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-green-500/10 text-green-400 rounded-2xl text-xs font-semibold border border-green-500/20">
            <Activity size={12} />
             实时
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {cards.map(({ label, value, icon: Icon, color, bg, trend }) => (
            <div key={label} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 hover:border-[#007AFF]/30 transition-all duration-200 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-2xl ${bg} flex items-center justify-center`}>
                  <Icon size={20} className={color} />
                </div>
                <span className="flex items-center gap-1 text-xs text-green-400 font-medium">
                  <TrendingUp size={10} /> {trend}
                </span>
              </div>
              <div className="text-3xl font-bold tracking-tight text-white">{value}</div>
              <div className="text-sm text-gray-400 mt-1">{label}</div>
            </div>
          ))}
        </div>

        {/* Activity placeholder */}
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 backdrop-blur-sm">
          <div className="flex items-center gap-2.5 mb-4">
            <Zap size={16} className="text-blue-400" />
            <h3 className="font-semibold text-sm text-gray-200">最近活动</h3>
          </div>
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-3">
              <Clock size={24} className="text-gray-600" />
            </div>
             <p className="text-sm text-gray-500">暂无最近活动</p>
             <p className="text-xs text-gray-600 mt-1">使用平台时活动将显示在此处</p>
          </div>
        </div>
      </div>
    </div>
  );
}
