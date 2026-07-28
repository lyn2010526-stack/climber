import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send, Users, Hash, MessageCircle,
  Bot, Crown, Eye, Loader2, PanelLeft, X,
} from 'lucide-react';

interface GroupMember {
  id: string;
  agent_id: string;
  role: string;
  status: string;
  message_count: number;
}

interface GroupMessage {
  id: string;
  sender_name: string;
  content: string;
  message_type: string;
  created_at: string;
}

interface GroupRoomProps {
  groupId: string;
  onLeave: () => void;
}

const ROLE_ICONS: Record<string, any> = {
  moderator: Crown,
  participant: Bot,
  observer: Eye,
};

const ROLE_COLORS: Record<string, string> = {
  moderator: 'text-amber-400',
  participant: 'text-blue-400',
  observer: 'text-gray-500',
};

const ROLE_LABELS: Record<string, string> = {
  moderator: '主持人',
  participant: '参与者',
  observer: '观察者',
};

export function GroupRoom({ groupId, onLeave }: GroupRoomProps) {
  const [messages, setMessages] = useState<GroupMessage[]>([]);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const getWsProtocol = () => window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const BASE_WS = `${getWsProtocol()}//${window.location.host}/api/v1/ws/groups/${groupId}`;

  useEffect(() => {
    // Fetch initial messages
    fetch(`/api/v1/groups/${groupId}/messages`)
      .then((r) => r.json())
      .then((data) => setMessages(data.messages || []))
      .catch(() => {});

    // Fetch group details for members
    fetch(`/api/v1/groups/${groupId}`)
      .then((r) => r.json())
      .then((data) => setMembers(data.members || []))
      .catch(() => {});

    // Connect WebSocket
    const ws = new WebSocket(`${BASE_WS}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'message' && msg.data) {
          setMessages((prev) => [...prev, {
            id: msg.data.id || Date.now().toString(),
            sender_id: msg.data.sender_id || '',
            sender_name: msg.data.sender_name || 'Unknown',
            content: msg.data.content || '',
            message_type: msg.data.message_type || 'text',
            created_at: msg.data.created_at || new Date().toISOString(),
          }]);
        } else if (msg.type === 'member_update' && msg.data) {
          setMembers((prev) => prev.map(m =>
            m.id === msg.data.member_id
              ? { ...m, status: msg.data.status || m.status }
              : m
          ));
        }
      } catch { /* skip */ }
    };

    return () => {
      ws.close();
    };
  }, [groupId]);

  // Periodic member refresh for real-time status
  useEffect(() => {
    const interval = setInterval(() => {
      fetch(`/api/v1/groups/${groupId}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.members && data.members.length > 0) {
            setMembers(data.members);
          }
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [groupId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(() => {
    if (!input.trim() || !wsRef.current || sending) return;
    setSending(true);

    wsRef.current.send(JSON.stringify({
      type: 'message',
      sender_name: 'You',
      content: input,
    }));
    setInput('');
    setSending(false);
  }, [input, sending]);

  return (
    <div className="flex h-full">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-10 flex items-center px-4 border-b border-gray-700 bg-gray-800/50">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="mr-2 p-1 rounded hover:bg-gray-700 text-gray-400 lg:hidden"
          >
            <PanelLeft size={14} />
          </button>
          <Hash size={14} className="text-blue-400 mr-2" />
           <span className="text-xs font-medium text-gray-100">群组讨论</span>
          <div className="ml-auto flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-[10px] text-gray-500">
              {connected ? '已连接' : '已断开'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-center py-8">
              <MessageCircle size={32} className="mx-auto text-gray-500/30" />
               <p className="text-xs text-gray-500 mt-2">暂无消息，开始讨论吧！</p>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center shrink-0">
                <Bot size={14} className="text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-100">{msg.sender_name}</span>
                  <span className="text-[10px] text-gray-500">
                    {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1 whitespace-pre-wrap break-words">
                  {msg.content}
                </p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-3 border-t border-gray-700 bg-gray-800/30">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
               placeholder="输入消息..."
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || sending || !connected}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            </button>
          </div>
        </div>
      </div>

      {/* Member Sidebar */}
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      <div className={`fixed inset-y-0 right-0 w-56 border-l border-gray-700 bg-gray-800/30 flex flex-col transform transition-transform duration-300 lg:relative lg:translate-x-0 z-50 ${sidebarOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="h-10 flex items-center px-3 border-b border-gray-700">
          <Users size={12} className="text-gray-500 mr-2" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
             成员 ({members.length})
          </span>
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto p-1 rounded hover:bg-gray-700 text-gray-400 lg:hidden"
          >
            <X size={12} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {members.map((member) => {
            const Icon = ROLE_ICONS[member.role] || Bot;
            const isOnline = member.status === 'active';
            return (
              <div
                key={member.id}
                className={`flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                  isOnline ? 'bg-gray-700/30 hover:bg-gray-700/50' : 'opacity-60'
                }`}
              >
                <div className="relative">
                  <Icon size={12} className={ROLE_COLORS[member.role] || 'text-gray-500'} />
                  {isOnline && (
                    <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full border border-gray-800 animate-pulse" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-gray-100 truncate">{member.agent_id.slice(0, 8)}</p>
                   <p className="text-[9px] text-gray-500">{ROLE_LABELS[member.role] || member.role}</p>
                </div>
                {isOnline && (
                  <span className="text-[8px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded-full">
                    在线
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div className="p-2 border-t border-gray-700">
          <button
            onClick={onLeave}
            className="w-full py-1.5 text-[10px] text-gray-500 hover:text-red-400 transition-colors"
          >
             退出群组
          </button>
        </div>
      </div>
    </div>
  );
}
