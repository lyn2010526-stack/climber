import { Brain, MemoryStick, Search, Clock } from 'lucide-react';

export default function MemoryPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-2xl bg-purple-500/10 text-purple-400">
          <Brain size={20} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">记忆管理</h1>
          <p className="text-xs text-gray-500">Agent 记忆系统的四层架构</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
          <div className="flex items-center gap-2 mb-3">
            <MemoryStick size={16} className="text-blue-400" />
            <h3 className="text-sm font-semibold text-white">工作记忆 (L1)</h3>
          </div>
          <p className="text-xs text-gray-500">当前任务上下文，单次执行生命周期</p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Clock size={16} className="text-green-400" />
            <h3 className="text-sm font-semibold text-white">情景记忆 (L2)</h3>
          </div>
          <p className="text-xs text-gray-500">过去的事件和经验，带时间戳和重要性评分</p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Search size={16} className="text-purple-400" />
            <h3 className="text-sm font-semibold text-white">语义记忆 (L3)</h3>
          </div>
          <p className="text-xs text-gray-500">结构化知识和事实</p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={16} className="text-amber-400" />
            <h3 className="text-sm font-semibold text-white">身份记忆 (L4)</h3>
          </div>
          <p className="text-xs text-gray-500">Agent 的人格和价值观</p>
        </div>
      </div>
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-8 text-center">
        <p className="text-sm text-gray-500">记忆管理功能开发中</p>
        <p className="text-xs text-gray-600 mt-1">Agent 可通过 remember/recall/forget 工具自主管理记忆</p>
      </div>
    </div>
  );
}
