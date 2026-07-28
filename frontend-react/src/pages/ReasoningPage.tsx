import { ReasoningPanel } from '../components/workspace/ReasoningPanel';

export function ReasoningPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-white/5 bg-[#0F0F14]/80 backdrop-blur-xl">
        <h1 className="text-lg font-bold text-white">推理引擎</h1>
        <p className="text-xs text-gray-400 mt-0.5">
          多策略推理：思维树、深度反思、辩论
        </p>
      </div>
      <div className="flex-1 overflow-hidden">
        <ReasoningPanel />
      </div>
    </div>
  );
}
