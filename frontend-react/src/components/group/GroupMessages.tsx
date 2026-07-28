import { useRef, useEffect } from 'react';
import { Bot, MessageCircle } from 'lucide-react';

interface GroupMessage {
  id: string;
  sender_name: string;
  content: string;
  message_type: string;
  created_at: string;
}

interface GroupMessagesProps {
  messages: GroupMessage[];
  currentSpeaker?: string | null;
  isEmpty?: boolean;
}

const SENDER_COLORS: Record<string, string> = {
  moderator: 'bg-amber-500/10 border-warning/20',
  participant: 'bg-blue-600/10 border-blue-500/20',
  system: 'bg-gray-700 border-gray-700',
};

export function GroupMessages({ messages, currentSpeaker, isEmpty }: GroupMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (isEmpty || messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <MessageCircle size={40} className="mx-auto text-gray-500/20" />
           <p className="text-xs text-gray-500 mt-3">此讨论暂无消息</p>
           <p className="text-[10px] text-gray-500/60 mt-1">开始对话即可查看消息</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.map((msg, idx) => {
        const isSystem = msg.message_type === 'system';
        const isCurrentSpeaker = msg.sender_name === currentSpeaker;
        const prevMsg = idx > 0 ? messages[idx - 1] : undefined;
        const showSpeaker = !prevMsg || prevMsg.sender_name !== msg.sender_name;

        if (isSystem) {
          return (
            <div key={msg.id} className="flex justify-center">
              <span className="px-3 py-1 bg-gray-700 rounded-full text-[10px] text-gray-500">
                {msg.content}
              </span>
            </div>
          );
        }

        return (
          <div key={msg.id} className={`flex items-start gap-3 ${!showSpeaker ? 'pl-11' : ''}`}>
            {showSpeaker && (
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                isCurrentSpeaker ? SENDER_COLORS['moderator'] : SENDER_COLORS['participant']
              }`}>
                <Bot size={14} className={isCurrentSpeaker ? 'text-amber-400' : 'text-blue-400'} />
              </div>
            )}
            <div className="flex-1 min-w-0">
              {showSpeaker && (
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-gray-100">
                    {msg.sender_name}
                  </span>
                  <span className="text-[10px] text-gray-500">
                    {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                  </span>
                  {isCurrentSpeaker && (
                    <span className="px-1.5 py-0.5 text-[9px] bg-blue-600/10 text-blue-400 rounded">
                      Speaking
                    </span>
                  )}
                </div>
              )}
              <p className="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap break-words">
                {msg.content}
              </p>
            </div>
          </div>
        );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
}
