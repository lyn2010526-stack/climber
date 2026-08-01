import React, { useState } from 'react';
import {
  Play, Square, RotateCcw, Code2, Terminal,
  CheckCircle2, XCircle, Clock,
  Zap, FileText, GitBranch, Eye,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface ExecutionStep {
  id: string;
  type: 'plan' | 'code' | 'execution' | 'output' | 'error';
  status: 'pending' | 'running' | 'success' | 'error';
  content: string;
  duration?: number;
  toolName?: string;
}

const mockSteps: ExecutionStep[] = [
  { id: '1', type: 'plan', status: 'success', content: '分析需求：实现一个快速排序算法' },
  { id: '2', type: 'plan', status: 'success', content: '设计算法步骤和边界条件' },
  { id: '3', type: 'code', status: 'success', content: 'def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)' },
  { id: '4', type: 'execution', status: 'success', content: '执行中...', duration: 120 },
  { id: '5', type: 'output', status: 'success', content: '[1, 2, 3, 5, 6, 8, 9]', duration: 120 },
];

const stepTypeConfig = {
  plan: { icon: GitBranch, label: '计划', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  code: { icon: Code2, label: '代码', color: 'text-violet-400', bg: 'bg-violet-500/10' },
  execution: { icon: Terminal, label: '执行', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  output: { icon: FileText, label: '输出', color: 'text-green-400', bg: 'bg-green-500/10' },
  error: { icon: XCircle, label: '错误', color: 'text-red-400', bg: 'bg-red-500/10' },
};

const statusIcon = {
  pending: Clock,
  running: Zap,
  success: CheckCircle2,
  error: XCircle,
};

export function CodeAgentPanel() {
  const [code, setCode] = useState('# 在此编写代码\ndef hello():\n    print("Hello, World!")');
  const [output, setOutput] = useState('');
  const [steps] = useState(mockSteps);
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [showPlan, setShowPlan] = useState(true);

  const handleRun = () => {
    setRunning(true);
    setOutput('');
    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep >= steps.length) {
        clearInterval(interval);
        setRunning(false);
        setOutput('Hello, World!');
        return;
      }
      setActiveStep(steps[currentStep]!.id);
      currentStep++;
    }, 800);
  };

  const handleStop = () => {
    setRunning(false);
    setActiveStep(null);
  };

  return (
    <div className="flex h-full">
      {/* Left: Code editor & output */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-[11px] text-gray-400 font-mono">main.py</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {running ? (
              <button
                onClick={handleStop}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-[11px] font-medium hover:bg-red-500/15 transition-all"
              >
                <Square size={12} />
                停止
              </button>
            ) : (
              <button
                onClick={handleRun}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 text-green-400 text-[11px] font-medium hover:bg-green-500/15 transition-all"
              >
                <Play size={12} />
                运行
              </button>
            )}
            <button className="p-1.5 rounded-lg bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all">
              <RotateCcw size={13} />
            </button>
          </div>
        </div>

        {/* Code area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <textarea
              value={code}
              onChange={e => setCode(e.target.value)}
              className="w-full h-full p-4 bg-transparent text-sm text-gray-200 font-mono leading-relaxed resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>

          {/* Output panel */}
          <div className="h-40 border-t border-white/[0.06] flex flex-col">
            <div className="flex items-center justify-between px-4 py-2">
              <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">执行输出</span>
              <button
                onClick={() => setOutput('')}
                className="text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
              >
                清空
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-4 pb-3">
              {running && (
                <div className="flex items-center gap-2 text-xs text-amber-400">
                  <div className="w-3 h-3 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
                  执行中...
                </div>
              )}
              {output && (
                <pre className="text-xs text-green-400 font-mono">{output}</pre>
              )}
              {!running && !output && (
                <p className="text-xs text-gray-600">点击运行按钮执行代码</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Execution trace */}
      <div className="w-80 border-l border-white/[0.06] flex flex-col bg-[#0D0D12]/50">
        <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-400">执行追踪</span>
          <button
            onClick={() => setShowPlan(!showPlan)}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] text-gray-500 hover:text-gray-300 hover:bg-white/[0.04] transition-all"
          >
            <Eye size={11} />
            {showPlan ? '隐藏计划' : '显示计划'}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="space-y-2">
            {steps.filter(s => showPlan || s.type !== 'plan').map((step, i, arr) => {
              const typeConfig = stepTypeConfig[step.type];
              const StatusIcon = statusIcon[step.status];
              const isActive = activeStep === step.id;

              return (
                <div key={step.id} className="flex gap-2">
                  {/* Timeline */}
                  <div className="flex flex-col items-center">
                    <div className={cn(
                      'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-all',
                      typeConfig.bg, isActive && 'ring-2 ring-offset-1 ring-offset-[#0D0D12] ring-blue-500/50'
                    )}>
                      <StatusIcon size={12} className={cn(
                        typeConfig.color,
                        step.status === 'running' && 'animate-pulse'
                      )} />
                    </div>
                    {i < arr.length - 1 && (
                      <div className={cn(
                        'w-px flex-1 my-1',
                        step.status === 'success' ? 'bg-green-500/20' : 'bg-white/[0.06]'
                      )} />
                    )}
                  </div>

                  {/* Content */}
                  <div className={cn(
                    'flex-1 pb-3 rounded-lg transition-all',
                    isActive && 'bg-white/[0.03]'
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('text-[10px] font-medium', typeConfig.color)}>
                        {typeConfig.label}
                      </span>
                      {step.duration && (
                        <span className="text-[10px] text-gray-600">{step.duration}ms</span>
                      )}
                    </div>
                    <pre className="text-[11px] text-gray-400 font-mono leading-relaxed whitespace-pre-wrap">
                      {step.content}
                    </pre>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
