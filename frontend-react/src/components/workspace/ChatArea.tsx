import { useState, useRef, useEffect } from 'react';
import { Send, Square, Search, X } from 'lucide-react';
import { Sparkles, Bot, Workflow, Users } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { usePersistentState } from '../../hooks/usePersistentState';
import { MessageRenderer } from '../messages/MessageRenderer';
import { StreamingIndicator } from './StreamingIndicator';
import { TaskChecklist } from './TaskChecklist';
import { NativeApprovalDialog } from './NativeApprovalDialog';
import { api } from '../../api';

interface ApprovalQueueItem {
  id: string;
  command: string;
  riskLevel: 'low' | 'medium' | 'high';
  timestamp: number;
}

export function ChatArea() {
  const { activeSessionId, sessions, addMessage, updateSession, tasks, permissionMode } = useWorkspaceStore();
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [checklistOpen, setChecklistOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [, setApprovalQueue] = usePersistentState<ApprovalQueueItem[]>('approval_queue', []);
  const [currentApproval, setCurrentApproval] = useState<ApprovalQueueItem | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId);

  const filteredMessages = activeSession?.messages.filter(msg => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
    return content.toLowerCase().includes(q);
  }) || [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming || !activeSessionId) return;
    const msg = input.trim();
    setInput('');

    // Add user message
    addMessage(activeSessionId, {
      id: `user-${Date.now()}`,
      type: 'user',
      content: msg,
      timestamp: Date.now(),
    });

    setIsStreaming(true);
    updateSession(activeSessionId, { status: 'running' });

    let assistantContent = '';
    let toolCalls: any[] = [];

    try {
      await api.chatStream(activeSessionId!, msg, (event) => {
        if (event.event === 'text') {
          const data = JSON.parse(event.data);
          assistantContent += data.content || '';
          addMessage(activeSessionId, {
            id: `assistant-${Date.now()}`,
            type: 'thinking',
            content: { text: assistantContent },
            timestamp: Date.now(),
            metadata: { tokens: data.tokens },
          });
        } else if (event.event === 'tool_call') {
          const data = JSON.parse(event.data);
          toolCalls.push(data);
          addMessage(activeSessionId, {
            id: `tool-call-${Date.now()}`,
            type: 'tool-call',
            content: { name: data.name, arguments: data.arguments },
            timestamp: Date.now(),
            metadata: { status: 'running', toolName: data.name, toolArgs: data.arguments },
          });
          if (permissionMode === 'native' && data.name?.startsWith('native_')) {
            const cmd = typeof data.arguments === 'string' ? data.arguments : JSON.stringify(data.arguments || {});
            const item: ApprovalQueueItem = {
              id: `approval-${Date.now()}`,
              command: cmd,
              riskLevel: data.name.includes('run') ? 'high' : 'medium',
              timestamp: Date.now(),
            };
            setApprovalQueue(prev => [...prev, item]);
            setCurrentApproval(item);
          }
        } else if (event.event === 'tool_result') {
          const data = JSON.parse(event.data);
          addMessage(activeSessionId, {
            id: `tool-result-${Date.now()}`,
            type: 'tool-result',
            content: data.result,
            timestamp: Date.now(),
            metadata: { status: 'success', toolName: data.tool_name },
          });
        } else if (event.event === 'done') {
          setIsStreaming(false);
          updateSession(activeSessionId, { status: 'idle' });
        }
      });
    } catch (e) {
      setIsStreaming(false);
      updateSession(activeSessionId, { status: 'error' });
    }
  };

  if (!activeSession) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-lg px-6">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-[#007AFF] to-[#AF52DE] flex items-center justify-center mx-auto mb-6 shadow-lg shadow-blue-500/20">
            <Sparkles size={32} className="text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">欢迎使用 Climber</h2>
          <p className="text-gray-400 text-sm mb-8 leading-relaxed">
            生产级 AI Agent 平台，支持 ReAct 推理、多智能体协作、<br />
            3D 推理引擎和 Apple 风格工作区。
          </p>
          <div className="grid grid-cols-3 gap-3 mb-8">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <Bot size={20} className="text-blue-400 mx-auto mb-2" />
              <p className="text-xs text-gray-400">多模型支持</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <Workflow size={20} className="text-purple-400 mx-auto mb-2" />
              <p className="text-xs text-gray-400">工作流编排</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <Users size={20} className="text-green-400 mx-auto mb-2" />
              <p className="text-xs text-gray-400">多智能体协作</p>
            </div>
          </div>
          <p className="text-xs text-gray-500">选择或创建会话以开始</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Native Approval Dialog */}
      {currentApproval && (
        <NativeApprovalDialog
          isOpen={true}
          command={currentApproval.command}
          riskLevel={currentApproval.riskLevel}
          onAllow={() => {
            setCurrentApproval(null);
            setApprovalQueue(prev => prev.filter(item => item.id !== currentApproval.id));
          }}
          onAllowAlways={() => {
            setCurrentApproval(null);
            setApprovalQueue(prev => prev.filter(item => item.id !== currentApproval.id));
          }}
          onDeny={() => {
            setCurrentApproval(null);
            setApprovalQueue(prev => prev.filter(item => item.id !== currentApproval.id));
          }}
        />
      )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {searchQuery && (
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg">
              <Search size={12} className="text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索消息..."
                className="flex-1 bg-transparent text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none"
                autoFocus
              />
              <button
                onClick={() => setSearchQuery('')}
                className="text-gray-500 hover:text-gray-200"
              >
                <X size={12} />
              </button>
            </div>
          )}
          {activeSession.messages.length === 0 && !searchQuery && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mx-auto mb-4">
                  <Sparkles size={24} className="text-blue-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">开始新的对话</h3>
                <p className="text-gray-400 text-sm mb-6">输入任何问题或任务，Climber 将为你自主执行。</p>
                <div className="flex flex-wrap justify-center gap-2">
                  <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-gray-400">帮我分析代码</span>
                  <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-gray-400">写一个 Python 脚本</span>
                  <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-gray-400">解释这个错误</span>
                </div>
              </div>
            </div>
          )}
          {filteredMessages.map((msg) => (
            <div key={msg.id} className="message-enter">
              <MessageRenderer message={msg} />
            </div>
          ))}
          {searchQuery && filteredMessages.length === 0 && (
            <div className="text-center py-8">
              <p className="text-xs text-gray-500">未找到匹配的消息</p>
            </div>
          )}
        {isStreaming && (
          <div className="flex justify-start">
            <StreamingIndicator text="Thinking..." type="thinking" />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Task Checklist */}
      {tasks.length > 0 && (
        <TaskChecklist
          tasks={tasks}
          isVisible={checklistOpen}
          onToggle={() => setChecklistOpen(!checklistOpen)}
        />
      )}

      {/* Input */}
      <div className="border-t border-gray-700 p-3 bg-gray-800/50 backdrop-blur-sm">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <button
            onClick={() => setSearchQuery(prev => prev ? '' : '')}
            className={`px-3 py-2.5 rounded-xl transition-colors ${searchQuery ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400 hover:text-gray-200'}`}
            title="搜索消息"
          >
            <Search size={16} />
          </button>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
             placeholder="输入消息...（Enter 发送）"
            className="flex-1 px-4 py-2.5 bg-gray-700 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50 transition-colors"
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button
               onClick={() => { setIsStreaming(false); if (activeSessionId) updateSession(activeSessionId, { status: 'idle' }); }}
              className="px-3 py-2.5 bg-red-500 hover:bg-red-500/80 text-white rounded-xl transition-colors"
            >
              <Square size={16} />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="px-3 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors disabled:opacity-30 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
