import EvalDashboard from '../components/eval/EvalDashboard';

export default function EvalPage() {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-4 py-2 border-b border-gray-700 bg-gray-800/50">
        <h2 className="text-lg font-semibold text-gray-200">效果评估</h2>
        <p className="text-xs text-gray-500">运行自动化测试以衡量智能体质量</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        <EvalDashboard />
      </div>
    </div>
  );
}
