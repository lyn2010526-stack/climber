import { useState } from 'react';
import {
  ChevronDown, ChevronRight, Terminal, CheckCircle2, AlertCircle,
  Loader2, Brain, Info, Bot, Code2, Clock,
} from 'lucide-react';
import type { Message } from '../../store/workspace';
import { useWorkspaceStore } from '../../store/workspace';

function formatTime(timestamp: number): string {
  const d = new Date(timestamp);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// ── Message Factory ──

export function MessageRenderer({ message }: { message: Message }) {
  const expertMode = useWorkspaceStore((s) => s.expertMode);

  switch (message.type) {
    case 'user':
      return <UserMessage content={message.content} timestamp={message.timestamp} />;
    case 'thinking':
      return expertMode ? <ThinkingBlock content={message.content} metadata={message.metadata} /> : null;
    case 'tool-call':
      return <ToolCallCard content={message.content} metadata={message.metadata} expertMode={expertMode} />;
    case 'tool-result':
      return <ToolResultCard content={message.content} metadata={message.metadata} expertMode={expertMode} />;
    case 'reflection':
      return expertMode ? <ReflectionCard content={message.content} metadata={message.metadata} /> : null;
    case 'system':
      return <SystemNotification content={message.content} metadata={message.metadata} timestamp={message.timestamp} />;
    default:
       return expertMode ? <div className="text-gray-500 text-sm">未知消息类型</div> : null;
  }
}

// ── User Message ──

function UserMessage({ content, timestamp }: { content: string; timestamp: number }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[70%] bg-blue-600 rounded-2xl rounded-br-md px-4 py-2.5 text-sm text-white shadow-lg shadow-blue-500/10">
        <div>{content}</div>
        <div className="text-[10px] text-blue-200/70 mt-1 text-right">{formatTime(timestamp)}</div>
      </div>
    </div>
  );
}

// ── Thinking Block ──

function ThinkingBlock({ content, metadata }: { content: any; metadata?: Message['metadata'] }) {
  const [expanded, setExpanded] = useState(false);
  const isDeepReflection = content?.type === 'deep_reflection';

  return (
    <div className={`max-w-[85%] rounded-xl border ${isDeepReflection ? 'border-blue-500/20 bg-blue-600/5' : 'border-gray-700/50 bg-gray-800'}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-gray-700/50/50 rounded-xl transition-colors"
      >
        <div className={`w-1 h-4 rounded-full ${isDeepReflection ? 'bg-blue-600' : 'bg-text-muted'}`} />
        {isDeepReflection ? (
          <Brain size={14} className="text-blue-400" />
        ) : (
          <Bot size={14} className="text-gray-500" />
        )}
        <span className={`text-xs font-medium ${isDeepReflection ? 'text-blue-400' : 'text-gray-500'}`}>
          {isDeepReflection ? 'Deep Reflection' : 'Thinking'}
        </span>
        {metadata?.tokens && (
          <span className="text-xs text-gray-500 ml-auto">{metadata.tokens} tokens</span>
        )}
        {expanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
      </button>
      {expanded && (
        <div className="px-4 pb-3 pl-10">
          <p className="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap">
            {typeof content === 'string' ? content : content?.text || JSON.stringify(content, null, 2)}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Tool Call Card ──

function ToolCallCard({ content, metadata, expertMode }: { content: any; metadata?: Message['metadata']; expertMode: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const toolName = content?.name || metadata?.toolName || 'unknown';
  const args = content?.arguments || metadata?.toolArgs || {};
  const status = metadata?.status || 'running';

  const statusConfig = {
    pending: { color: 'text-amber-400', dot: 'bg-amber-500', label: 'Queued' },
    running: { color: 'text-blue-400', dot: 'bg-blue-600 animate-pulse', label: 'Running' },
    success: { color: 'text-green-400', dot: 'bg-green-500', label: 'Success' },
    error: { color: 'text-red-400', dot: 'bg-red-500', label: 'Failed' },
    cancelled: { color: 'text-gray-500', dot: 'bg-text-muted', label: 'Cancelled' },
  };

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.running;

  return (
    <div className="max-w-[85%] tool-call-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="tool-call-header w-full text-left cursor-pointer hover:bg-gray-700/50/50 transition-colors"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className={`status-dot ${status}`} style={{ width: 6, height: 6 }} />
          <Terminal size={13} className={config.color} />
          <span className="text-xs font-medium text-gray-100 truncate">{toolName}</span>
          {Object.keys(args).length > 0 && (
            <span className="text-xs text-gray-500 truncate">
              ({Object.keys(args).join(', ')})
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs ${config.color}`}>{config.label}</span>
          {metadata?.durationMs && (
            <span className="text-xs text-gray-500">{(metadata.durationMs / 1000).toFixed(1)}s</span>
          )}
          {metadata?.retryCount && metadata.retryCount > 0 && (
            <span className="text-xs text-amber-400">retry:{metadata.retryCount}</span>
          )}
          {status === 'running' && <Loader2 size={12} className="text-blue-400 animate-spin" />}
          {expanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
        </div>
      </button>

      {metadata?.blockReason && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/20">
          <div className="flex items-center gap-2">
            <AlertCircle size={12} className="text-red-400" />
            <span className="text-xs text-red-400">Blocked: {metadata.blockReason}</span>
          </div>
        </div>
      )}

      {expanded && (
        <div className="p-3 space-y-2">
          {Object.entries(args).map(([key, val]) => (
            <div key={key}>
              <span className="text-xs text-gray-500 font-medium">{key}:</span>
              <pre className="code-block text-xs mt-0.5">{typeof val === 'string' ? val : JSON.stringify(val, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}

      {expertMode && metadata?.tokens !== undefined && (
        <div className="px-4 py-1.5 border-t border-gray-700/50 flex items-center gap-3 text-[10px] text-gray-500">
          <span className="flex items-center gap-1"><Code2 size={10} /> {metadata.tokens} tokens</span>
        </div>
      )}
    </div>
  );
}

// ── Tool Result Card ──

function ToolResultCard({ content, metadata, expertMode }: { content: any; metadata?: Message['metadata']; expertMode: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const toolName = metadata?.toolName || 'unknown';
  const resultStr = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
  const isLong = resultStr.length > 2000;
  const status = metadata?.status || 'success';
  void expertMode;

  return (
    <div className="max-w-[85%] tool-call-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="tool-call-header w-full text-left cursor-pointer hover:bg-gray-700/50/50 transition-colors"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <CheckCircle2 size={13} className={status === 'error' ? 'text-red-400' : 'text-green-400'} />
          <span className="text-xs font-medium text-green-400 truncate">{toolName}</span>
          <span className="text-xs text-gray-500 truncate">
            {resultStr.slice(0, 80)}{resultStr.length > 80 ? '...' : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {metadata?.tokens && <span className="text-xs text-gray-500">{metadata.tokens} tok</span>}
           {isLong && <span className="text-xs text-blue-400">长输出</span>}
          {expanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
        </div>
      </button>
      {expanded && (
        <div className="p-3">
          <pre className="code-block text-xs max-h-80 overflow-y-auto">{resultStr}</pre>
          <div className="flex gap-2 mt-2">
            <button className="text-xs text-blue-400 hover:text-blue-400 px-2 py-1 rounded bg-blue-600/10">
               导出到文件
            </button>
            <button className="text-xs text-blue-400 hover:text-blue-400 px-2 py-1 rounded bg-blue-600/10">
               添加到记忆
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Reflection Card ──

function ReflectionCard({ content, metadata }: { content: any; metadata?: Message['metadata'] }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="max-w-[85%] rounded-xl border border-blue-500/20 bg-blue-600/5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-blue-600/5 transition-colors rounded-xl"
      >
        <Brain size={14} className="text-blue-400" />
        <span className="text-xs font-medium text-blue-400">Self-Reflection</span>
        {metadata?.tokens && <span className="text-xs text-gray-500 ml-auto">{metadata.tokens} tokens</span>}
        {expanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
      </button>
      {expanded && (
        <div className="px-4 pb-3">
          <p className="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap">
            {typeof content === 'string' ? content : content?.text || JSON.stringify(content, null, 2)}
          </p>
        </div>
      )}
    </div>
  );
}

// ── System Notification ──

function SystemNotification({ content, metadata, timestamp }: { content: any; metadata?: Message['metadata']; timestamp: number }) {
  const level = metadata?.status || 'success';
  const isError = level === 'error';
  const bgColor = isError ? 'bg-red-500/10 border-red-500/30' : 'bg-blue-600/5 border-blue-500/20';
  const iconColor = isError ? 'text-red-400' : 'text-blue-400';

  return (
    <div className={`mx-auto max-w-md px-4 py-2.5 rounded-xl border ${bgColor} flex items-center gap-2`}>
      <Info size={14} className={iconColor} />
      <span className="text-xs text-gray-400 flex-1">
        {typeof content === 'string' ? content : JSON.stringify(content)}
      </span>
      <span className="text-[10px] text-gray-500 flex items-center gap-1">
        <Clock size={10} />
        {formatTime(timestamp)}
      </span>
    </div>
  );
}
