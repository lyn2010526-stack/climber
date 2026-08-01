import React, { useState, useEffect, useRef } from 'react';
import {
  Zap, CheckCircle2, XCircle, Clock, ChevronRight,
  Terminal, Code2, FileText, Loader2, Brain,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface StreamItem {
  id: string;
  type: 'thinking' | 'token' | 'tool-call' | 'tool-result' | 'code' | 'plan-update' | 'progress';
  content: string;
  status?: 'pending' | 'running' | 'success' | 'error';
  toolName?: string;
  duration?: number;
  progress?: number;
  timestamp: number;
}

const mockStream: StreamItem[] = [
  { id: '1', type: 'thinking', content: '正在分析用户需求...', status: 'success', timestamp: 1000 },
  { id: '2', type: 'token', content: '我将帮您实现这个功能。首先，让我查看项目结构。', timestamp: 1500 },
  { id: '3', type: 'tool-call', content: '读取项目文件结构', status: 'success', toolName: 'list_files', duration: 230, timestamp: 2000 },
  { id: '4', type: 'tool-result', content: '发现 15 个文件，3 个目录', status: 'success', timestamp: 2230 },
  { id: '5', type: 'thinking', content: '正在规划实现方案...', status: 'success', timestamp: 2500 },
  { id: '6', type: 'plan-update', content: '1. 创建组件文件\n2. 实现核心逻辑\n3. 添加样式\n4. 编写测试', timestamp: 3000 },
  { id: '7', type: 'code', content: 'function processData(input) {\n  return input.map(item => ({\n    ...item,\n    processed: true\n  }));\n}', timestamp: 3500 },
  { id: '8', type: 'progress', content: '正在生成文件...', progress: 65, status: 'running', timestamp: 4000 },
  { id: '9', type: 'tool-call', content: '写入文件: ProcessComponent.tsx', status: 'success', toolName: 'write_file', duration: 89, timestamp: 4200 },
  { id: '10', type: 'tool-result', content: '文件写入成功', status: 'success', timestamp: 4289 },
];

const typeConfig = {
  thinking: { icon: Brain, color: 'text-blue-400', bg: 'bg-blue-500/10', label: '思考中' },
  token: { icon: ChevronRight, color: 'text-gray-300', bg: '', label: '' },
  'tool-call': { icon: Terminal, color: 'text-amber-400', bg: 'bg-amber-500/10', label: '工具调用' },
  'tool-result': { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10', label: '执行结果' },
  code: { icon: Code2, color: 'text-violet-400', bg: 'bg-violet-500/10', label: '代码生成' },
  'plan-update': { icon: FileText, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: '计划更新' },
  progress: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: '进度' },
};

export function StreamOutput() {
  const [items, setItems] = useState<StreamItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const streamRef = useRef<ReturnType<typeof setTimeout>>();

  const startStream = () => {
    setItems([]);
    setIsStreaming(true);
    let index = 0;

    const addNext = () => {
      if (index >= mockStream.length) {
        setIsStreaming(false);
        return;
      }
      const item = mockStream[index]!;
      setItems(prev => [...prev, { ...item, id: `${item.id}-${Date.now()}` }]);
      index++;
      streamRef.current = setTimeout(addNext, 600 + Math.random() * 400);
    };

    streamRef.current = setTimeout(addNext, 300);
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) clearTimeout(streamRef.current);
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [items]);

  return (
    <div className="flex flex-col h-full rounded-2xl border border-white/[0.06] bg-[#0D0D12]/80 backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full',
            isStreaming ? 'bg-green-500 animate-pulse' : 'bg-gray-600'
          )} />
          <span className="text-xs font-semibold text-gray-400">流式输出</span>
          {isStreaming && (
            <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-green-500/10 text-green-400 font-medium animate-pulse">
              实时
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {!isStreaming && (
            <button
              onClick={startStream}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-[11px] font-medium hover:bg-blue-500/15 transition-all"
            >
              <Zap size={12} />
              演示
            </button>
          )}
          <button
            onClick={() => { setItems([]); setIsStreaming(false); }}
            className="p-1.5 rounded-lg bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all"
          >
            <XCircle size={13} />
          </button>
        </div>
      </div>

      {/* Stream content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {items.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full">
            <Zap size={32} className="text-gray-700 mb-3" />
            <p className="text-sm text-gray-500">点击演示查看流式输出</p>
            <p className="text-xs text-gray-600 mt-1">实时展示智能体的思考和工具调用</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item, index) => {
              const config = typeConfig[item.type];
              const Icon = config.icon;

              return (
                <div
                  key={item.id}
                  className={cn(
                    'transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
                    'animate-[fadeSlideIn_0.3s_ease_forwards]'
                  )}
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  {item.type === 'token' ? (
                    <p className="text-sm text-gray-200 leading-relaxed pl-2">
                      {item.content}
                    </p>
                  ) : item.type === 'progress' ? (
                    <div className="p-3 rounded-xl bg-blue-500/[0.04] border border-blue-500/10">
                      <div className="flex items-center gap-2 mb-2">
                        <Loader2 size={13} className="text-blue-400 animate-spin" />
                        <span className="text-xs text-blue-400 font-medium">{item.content}</span>
                      </div>
                      <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-violet-500 rounded-full transition-all duration-500"
                          style={{ width: `${item.progress || 0}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500 mt-1 block text-right">{item.progress}%</span>
                    </div>
                  ) : (
                    <div className={cn('p-3 rounded-xl border', config.bg || 'bg-white/[0.02]', 'border-white/[0.04]')}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <Icon size={13} className={config.color} />
                        <span className={cn('text-[10px] font-medium', config.color)}>{config.label}</span>
                        {item.toolName && (
                          <code className="text-[10px] text-gray-500 font-mono">{item.toolName}</code>
                        )}
                        {item.duration && (
                          <span className="text-[10px] text-gray-600 ml-auto">{item.duration}ms</span>
                        )}
                        {item.status && (
                          <StatusBadge status={item.status} />
                        )}
                      </div>
                      <pre className="text-xs text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
                        {item.content}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
            {isStreaming && (
              <div className="flex items-center gap-2 pl-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[11px] text-gray-500">正在生成...</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config = {
    pending: { icon: Clock, color: 'text-gray-400', label: '等待' },
    running: { icon: Loader2, color: 'text-amber-400', label: '运行中' },
    success: { icon: CheckCircle2, color: 'text-green-400', label: '成功' },
    error: { icon: XCircle, color: 'text-red-400', label: '失败' },
  }[status] || { icon: Clock, color: 'text-gray-400', label: status };

  if (!config) return null;
  const Icon = config.icon;

  return (
    <span className={cn('flex items-center gap-1 text-[10px] ml-auto', config.color)}>
      <Icon size={10} className={status === 'running' ? 'animate-spin' : ''} />
      {config.label}
    </span>
  );
}
