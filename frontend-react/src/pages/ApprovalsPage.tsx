import { Bell, Clock } from 'lucide-react';

export default function ApprovalsPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-2xl bg-amber-500/10 text-amber-400">
          <Bell size={20} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">审批队列</h1>
          <p className="text-xs text-gray-500">待人工审批的工具调用</p>
        </div>
      </div>
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-8 text-center">
        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
          <Clock size={20} className="text-gray-500" />
        </div>
        <p className="text-sm text-gray-500">暂无待审批项</p>
        <p className="text-xs text-gray-600 mt-1">当 Agent 遇到需要人工确认的工具调用时，将在此显示</p>
      </div>
    </div>
  );
}
