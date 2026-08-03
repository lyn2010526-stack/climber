import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Square, Search, X, Paperclip } from 'lucide-react';
import { Sparkles, Bot, Workflow, Users } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { usePersistentState } from '../../hooks/usePersistentState';
import { MessageRenderer } from '../messages/MessageRenderer';
import { StreamingIndicator } from './StreamingIndicator';
import { TaskChecklist } from './TaskChecklist';
import { NativeApprovalDialog } from './NativeApprovalDialog';
import { api } from '../../api';

interface Attachment {
  id: string;
  name: string;
  size: number;
  type: string;
  preview: string | undefined;
}

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
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [showSlashCommands, setShowSlashCommands] = useState(false);
  const [, setApprovalQueue] = usePersistentState<ApprovalQueueItem[]>('approval_queue', []);
  const [currentApproval, setCurrentApproval] = useState<ApprovalQueueItem | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileAttach = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newAttachments: Attachment[] = files.map((file): Attachment => ({
      id: `attach-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      name: file.name,
      size: file.size,
      type: file.type,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
    }));
    setAttachments(prev => [...prev, ...newAttachments]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachments(prev => {
      const att = prev.find(a => a.id === id);
      if (att?.preview) URL.revokeObjectURL(att.preview);
      return prev.filter(a => a.id !== id);
    });
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInput(val);
    setShowSlashCommands(val === '/');
  }, []);

  const handleSlashCommand = useCallback((cmd: string) => {
    setInput(cmd + ' ');
    setShowSlashCommands(false);
    inputRef.current?.focus();
  }, []);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const slashCommands = [
    { cmd: '/help', desc: '查看帮助' },
    { cmd: '/clear', desc: '清除对话' },
    { cmd: '/export', desc: '导出对话' },
    { cmd: '/model', desc: '切换模型' },
    { cmd: '/agent', desc: '切换智能体' },
  ];

  const handleSend = async () => {
    if (!input.trim() || isStreaming || !activeSessionId) return;
    const msg = input.trim();
    setInput('');

    // Add user message
    addMessage(activeSessionId!, {
      id: `user-${Date.now()}`,
      type: 'user',
      content: msg,
      timestamp: Date.now(),
    });

    setIsStreaming(true);
    updateSession(activeSessionId!, { status: 'running' });

    let assistantContent = '';
    let toolCalls: any[] = [];
    let assistantMessageId = `assistant-${Date.now()}`;

    try {
      await api.chatStream(activeSessionId!, msg, (event) => {
        try {
          if (event.event === 'text') {
            const data = JSON.parse(event.data);
            assistantContent += data.content || '';
            addMessage(activeSessionId, {
              id: assistantMessageId,
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
          } else if (event.event === 'stopped') {
            setIsStreaming(false);
            updateSession(activeSessionId, { status: 'idle' });
          }
        } catch {
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
          <p className="text-[var(--color-text-secondary)] text-sm mb-8 leading-relaxed">
            生产级 AI Agent 平台，支持 ReAct 推理、多智能体协作、<br />
            3D 推理引擎和 Apple 风格工作区。
          </p>
          <div className="grid grid-cols-3 gap-3 mb-8">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <Bot size={20} className="text-blue-400 mx-auto mb-2" />
              <p className="text-xs text-[var(--color-text-muted)]">多模型支持</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <Workflow size={20} className="text-purple-400 mx-auto mb-2" />
              <p className="text-xs text-[var(--color-text-muted)]">工作流编排</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <Users size={20} className="text-green-400 mx-auto mb-2" />
              <p className="text-xs text-[var(--color-text-muted)]">多智能体协作</p>
            </div>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">选择或创建会话以开始</p>
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
            <div className="flex items-center gap-2 px-3 py-2 bg-[var(--color-bg-surface-1)]/50 border-[var(--color-border-subtle)] rounded-lg">
              <Search size={12} className="text-[var(--color-text-muted)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索消息..."
                className="flex-1 bg-transparent text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
                autoFocus
              />
              <button
                onClick={() => setSearchQuery('')}
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
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
                <p className="text-[var(--color-text-secondary)] text-sm mb-6">输入任何问题或任务，Climber 将为你自主执行。</p>
                <div className="flex flex-wrap justify-center gap-2">
                  <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-[var(--color-text-muted)]">帮我分析代码</span>
                  <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-[var(--color-text-muted)]">写一个 Python 脚本</span>
                  <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-[var(--color-text-muted)]">解释这个错误</span>
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
              <p className="text-xs text-[var(--color-text-muted)]">未找到匹配的消息</p>
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
      <div className="border-t border-white/[0.04] p-4 md:p-5" style={{
        backgroundColor: 'var(--color-bg-surface-1)',
        backdropFilter: 'blur(24px) saturate(180%)',
      }}>
        <div className="flex gap-2.5 max-w-4xl mx-auto">
          <button
            onClick={() => setSearchQuery(prev => prev ? '' : '')}
            className={`shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-150 ${searchQuery ? 'bg-[#5E6AD2] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/[0.04]'}`}
            style={{ border: '1px solid var(--color-border-subtle)' }}
            title="搜索消息"
          >
            <Search size={16} />
          </button>
          <div className="flex-1 flex flex-col gap-2">
            {/* Attachment Preview */}
            {attachments.length > 0 && (
              <div className="flex gap-2 flex-wrap">
                {attachments.map(att => (
                  <div key={att.id} className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs message-enter" style={{
                    backgroundColor: 'var(--color-bg-surface-2)',
                    border: '1px solid var(--color-border-subtle)',
                    color: 'var(--color-text-secondary)',
                  }}>
                    {att.preview && <img src={att.preview} alt={att.name} className="w-6 h-6 rounded object-cover" />}
                    <span className="truncate max-w-[100px]">{att.name}</span>
                    <span style={{ color: 'var(--color-text-muted)' }}>{formatFileSize(att.size)}</span>
                    <button onClick={() => removeAttachment(att.id)} className="hover:text-white transition-colors" style={{ color: 'var(--color-text-muted)' }}>
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={handleInputChange}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="输入消息...（Enter 发送，/ 斜杠命令）"
                className="flex-1 px-4 py-2.5 rounded-2xl text-sm focus:outline-none transition-all duration-200"
                style={{
                  backgroundColor: 'var(--color-bg-surface-2)',
                  border: '1px solid var(--color-border-subtle)',
                  color: 'var(--color-text-primary)',
                }}
                disabled={isStreaming}
              />
              <button
                onClick={() => { if (fileInputRef.current) fileInputRef.current.click(); }}
                className="shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-150 hover:bg-white/[0.04]"
                style={{ color: 'var(--color-text-muted)', border: '1px solid var(--color-border-subtle)' }}
                title="添加附件"
              >
                <Paperclip size={16} />
              </button>
              <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileAttach} />
              {isStreaming ? (
                <button
                  onClick={() => { setIsStreaming(false); if (activeSessionId) updateSession(activeSessionId!, { status: 'idle' }); }}
                  className="shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-150 hover:bg-red-500/20"
                  style={{ backgroundColor: 'rgba(239,68,68,0.15)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' }}
                >
                  <Square size={16} />
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-150 shadow-lg disabled:opacity-30 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: 'var(--color-accent)',
                    color: 'var(--color-accent-text)',
                    boxShadow: '0 4px 12px rgba(94,106,210,0.25)',
                  }}
                >
                  <Send size={16} />
                </button>
              )}
            </div>
            {/* Slash Commands */}
            {showSlashCommands && (
              <div className="rounded-2xl overflow-hidden message-enter" style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border-default)',
                boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
              }}>
                <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider" style={{
                  color: 'var(--color-text-muted)',
                  borderBottom: '1px solid var(--color-border-subtle)',
                }}>
                  斜杠命令
                </div>
                {slashCommands.map(cmd => (
                  <button
                    key={cmd.cmd}
                    onClick={() => handleSlashCommand(cmd.cmd)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors duration-150 hover:bg-white/[0.03]"
                    style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
                  >
                    <code className="text-xs font-mono px-2 py-0.5 rounded-lg" style={{
                      backgroundColor: 'var(--color-accent-subtle)',
                      color: 'var(--color-accent)',
                    }}>{cmd.cmd}</code>
                    <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{cmd.desc}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
