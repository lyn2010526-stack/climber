import { useState, useEffect, useRef, useCallback } from 'react';
import { TaskInput } from './TaskInput';
import { CollabMessage, type CollabMessage as CollabMessageType } from './CollabMessage';
import { ProgressHeader } from './ProgressHeader';
import { Send } from 'lucide-react';
import { api } from '../../api';

function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 9);
}

interface CollaborationConsoleProps {
  groupId: string;
  availableTasks?: Array<{ id: string; description: string }>;
}

export interface TaskOptions {
  processType?: 'sequential' | 'hierarchical' | 'group_chat';
  context?: string[];
  guardrails?: Array<{ name: string; description: string }>;
  humanReviewRequired?: boolean;
}

export function CollaborationConsole({ groupId, availableTasks = [] }: CollaborationConsoleProps) {
  const [messages, setMessages] = useState<CollabMessageType[]>([]);
  const [status, setStatus] = useState('idle');
  const [currentRound, setCurrentRound] = useState(0);
  const [maxRounds, setMaxRounds] = useState(5);
  const [activeMember, setActiveMember] = useState<string>('');
  const [totalTokens, _setTotalTokens] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | null>(null);

  // Timer for elapsed time
  useEffect(() => {
    if (status === 'running' || status === 'reviewing') {
      if (!startTime) setStartTime(Date.now());
      timerRef.current = window.setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - (startTime || Date.now())) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, [status, startTime]);

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${window.location.host}/api/v1/ws/groups/${groupId}?user_id=local`);
    wsRef.current = ws;

    ws.onopen = () => {
      setMessages(prev => [...prev, {
        id: genId(), memberId: 'system', memberName: 'System', role: 'system',
        content: '已连接到群组协作空间', timestamp: new Date().toISOString(),
      }] as CollabMessageType[]);
    };
    ws.onclose = () => { /* disconnected */ };
    ws.onmessage = (event) => {
      try {
        const msg: any = JSON.parse(event.data);
        handleWSMessage(msg);
      } catch { /* skip */ }
    };

    return () => ws.close();
  }, [groupId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleWSMessage = useCallback((msg: any) => {
    const data = msg.data || {};
    switch (msg.type) {
      case 'message':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: data.sender_id || 'system',
          memberName: data.sender_name || 'System',
          role: 'system',
          content: data.content || '',
          timestamp: data.created_at || new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'member_update':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: data.member_id || 'system',
          memberName: data.member_name || 'System',
          role: 'system',
          content: `成员状态更新: ${data.status || 'unknown'}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'task_update':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `任务状态更新: ${data.status || 'unknown'}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'system_message':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: data.content || '',
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'reviewer_error':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: data.member_id || 'system',
          memberName: data.member_name || 'Reviewer',
          role: 'system',
          content: `审查者错误: ${data.error || 'unknown'}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'guardrail_passed':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'Guardrail',
          role: 'system',
          content: `校验通过: ${data.guardrail_name || 'unnamed'} (尝试 ${data.attempt || 1}/${data.max_attempts || 1})`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'guardrail_failed':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'Guardrail',
          role: 'system',
          content: `校验失败: ${data.guardrail_name || 'unnamed'} - ${data.reason || 'no reason'} (尝试 ${data.attempt || 1}/${data.max_attempts || 1})`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'human_review_needed':
        setStatus('awaiting_human_review');
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'Human Review',
          role: 'system',
          content: `需要人工审批: ${data.content || '任务产出需要审核'}\n\n回复 "approve" 批准或 "reject" 拒绝`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'checkpoint_saved':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `断点已保存 (轮次 ${data.current_round || 0}/${data.max_rounds || 5})`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'memory_injected':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'Memory',
          role: 'system',
          content: `记忆已注入: ${data.memory_count || 0} 条相关记忆`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'manager_plan':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: data.manager_id || 'system',
          memberName: data.manager_name || 'Manager',
          role: 'system',
          content: `Manager 规划: ${data.plan || '无计划'}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'group_chat_message':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: data.sender_id || 'system',
          memberName: data.sender_name || 'Unknown',
          role: 'worker',
          content: data.content || '',
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'consensus_reached':
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `群组达成共识 (${data.consensus_keyword || 'default'})`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'task_started':
        setStatus('running');
        setMessages([{
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `任务已启动: ${data.task}`,
          timestamp: new Date().toISOString(),
        }]);
        break;

      case 'worker_start':
        setActiveMember(data.member_name);
        setStatus('running');
        break;

      case 'text_delta': {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.memberId === data.member_id && last.role === 'worker') {
            return [...prev.slice(0, -1), { ...last, content: last.content + (data.delta || '') }];
          }
          return [...prev, {
            id: genId(),
            memberId: data.member_id || '',
            memberName: data.member_name || 'Unknown',
            memberAvatar: data.member_avatar,
            role: 'worker',
            content: data.delta || '',
            timestamp: new Date().toISOString(),
          }] as CollabMessageType[];
        });
        break;
      }

      case 'worker_done': {
        const workerContent = data.content as string;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.memberId === data.member_id && last.role === 'worker') {
            const updated: CollabMessageType = { ...last, content: workerContent };
            return [...prev.slice(0, -1), updated];
          }
          return [...prev, {
            id: genId(),
            memberId: data.member_id || '',
            memberName: data.member_name || 'Unknown',
            memberAvatar: data.member_avatar,
            role: 'worker',
            content: workerContent,
            timestamp: new Date().toISOString(),
          }] as CollabMessageType[];
        });
        break;
      }

      case 'progress_update':
        setCurrentRound(data.current_round || 0);
        setMaxRounds(data.max_rounds || 5);
        setStatus(data.status || 'running');
        setActiveMember(data.active_member);
        break;

      case 'task_completed':
        setStatus('completed');
        setActiveMember('');
        setStartTime(null);
        setElapsedTime(0);
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `任务完成！最终产出:\n\n${data.final_output || ''}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'task_partial':
        setStatus('partial');
        setActiveMember('');
        setStartTime(null);
        setElapsedTime(0);
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `任务部分完成 (${data.rounds || 0} 轮):\n\n${data.final_output || ''}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;

      case 'task_failed':
        setStatus('failed');
        setActiveMember('');
        setStartTime(null);
        setElapsedTime(0);
        setMessages((prev) => [...prev, {
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `任务失败: ${data.error || 'unknown'}`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);
        break;
    }
  }, []);

  const startTask = useCallback(async (task?: string, rounds?: number, options?: TaskOptions) => {
    if (!task) return;
    setStartTime(Date.now());
    setElapsedTime(0);

    try {
      const resp = await api.createTask({
          group_id: groupId,
          description: task,
          max_rounds: rounds || 5,
          context: options?.context || [],
          guardrails: options?.guardrails || [],
          human_review_required: options?.humanReviewRequired || false,
        });

      if (resp.id) {
        setSessionId(resp.id);
        setMessages([{
          id: genId(),
          memberId: 'system',
          memberName: 'System',
          role: 'system',
          content: `任务已创建 (ID: ${resp.id.slice(0, 8)}...)`,
          timestamp: new Date().toISOString(),
        }] as CollabMessageType[]);

        await api.runTask(resp.id);
      }
    } catch (e: any) {
      setMessages([{
        id: genId(),
        memberId: 'system',
        memberName: 'System',
        role: 'system',
        content: `启动失败: ${e.message}`,
        timestamp: new Date().toISOString(),
      }] as CollabMessageType[]);
    }
  }, [groupId]);

  const pauseTask = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.pauseTask(sessionId);
      setStatus('paused');
      setStartTime(null);
      setElapsedTime(0);
    } catch (e: any) {
      setMessages((prev) => [...prev, {
        id: genId(),
        memberId: 'system',
        memberName: 'System',
        role: 'system',
        content: `暂停失败: ${e.message}`,
        timestamp: new Date().toISOString(),
      }] as CollabMessageType[]);
    }
  }, [sessionId]);

  const resumeTask = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.resumeTask(sessionId);
      setStatus('running');
      setStartTime(Date.now());
      setElapsedTime(0);
    } catch (e: any) {
      setMessages((prev) => [...prev, {
        id: genId(),
        memberId: 'system',
        memberName: 'System',
        role: 'system',
        content: `恢复失败: ${e.message}`,
        timestamp: new Date().toISOString(),
      }] as CollabMessageType[]);
    }
  }, [sessionId]);

  const stopTask = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.stopTask(sessionId);
      setStatus('stopped');
      setActiveMember('');
      setStartTime(null);
      setElapsedTime(0);
    } catch (e: any) {
      setMessages((prev) => [...prev, {
        id: genId(),
        memberId: 'system',
        memberName: 'System',
        role: 'system',
        content: `停止失败: ${e.message}`,
        timestamp: new Date().toISOString(),
      }] as CollabMessageType[]);
    }
  }, [sessionId]);

  const [inputMessage, setInputMessage] = useState('');

  const sendMessage = useCallback(() => {
    if (!inputMessage.trim() || !wsRef.current) return;
    const payload = {
      type: 'message',
      sender_id: 'current-user',
      sender_name: 'Current User',
      content: inputMessage.trim(),
      message_type: 'text',
    };
    wsRef.current.send(JSON.stringify(payload));
    setInputMessage('');
  }, [inputMessage]);

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <ProgressHeader
        status={status}
        currentRound={currentRound}
        maxRounds={maxRounds}
        activeMember={activeMember}
        totalTokens={totalTokens}
        elapsedTime={elapsedTime}
        onPause={pauseTask}
        onResume={resumeTask}
        onStop={stopTask}
      />

      <div className="flex-1 overflow-y-auto p-4 md:p-4 space-y-2">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-xs text-gray-500">配置 AI 成员后，输入任务开始自动协作</p>
            <p className="text-[10px] text-gray-500 mt-1">Worker 产出 → Reviewer 检查 → 纠正 → 通过</p>
          </div>
        )}
        {messages.map((msg) => (
          <CollabMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input + Task Input */}
      <div className="border-t border-gray-700 bg-gray-800/30">
        {/* Message Input */}
        <div className="p-3 md:p-3 border-b border-gray-700/50">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="输入消息..."
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
            />
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim()}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <Send size={14} />
            </button>
          </div>
        </div>

        <TaskInput
          onStart={startTask}
          onPause={pauseTask}
          onStop={stopTask}
          status={status === 'running' || status === 'reviewing' ? 'running' : status === 'paused' ? 'paused' : status === 'completed' ? 'idle' : 'idle'}
          availableTasks={availableTasks}
        />
      </div>
    </div>
  );
}
