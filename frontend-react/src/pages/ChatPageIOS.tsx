import { useState, type FormEvent } from 'react';
import { Plus, Send, Paperclip, Bot } from 'lucide-react';
import { IOSPage, IOSNavbar, IOSToaster, toast } from '../components/ios';
import { cn } from '../lib/utils';

interface ChatMessage {
  id: number;
  sender: 'user' | 'agent';
  name: string;
  content: string;
  time: string;
}

const initialMessages: ChatMessage[] = [
  {
    id: 1,
    sender: 'user',
    name: '我',
    content: '帮我分析一下这段代码的性能问题',
    time: '10:23',
  },
  {
    id: 2,
    sender: 'agent',
    name: '助手',
    content: '我看到这段代码有几个性能瓶颈：循环中存在重复计算、数据库查询未使用索引、以及内存泄漏风险。',
    time: '10:24',
  },
  {
    id: 3,
    sender: 'user',
    name: '我',
    content: '能给出优化建议吗？',
    time: '10:25',
  },
  {
    id: 4,
    sender: 'agent',
    name: '助手',
    content: '当然，以下是几个优化方向：提取循环外重复计算、为查询字段添加索引、及时释放不再使用的对象引用。',
    time: '10:26',
  },
];

export default function ChatPageIOS() {
  const [messages] = useState<ChatMessage[]>(initialMessages);
  const [inputValue, setInputValue] = useState('');

  const handleSend = (e: FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    toast.success('消息已发送');
    setInputValue('');
  };

  const handleNewChat = () => {
    toast('已创建新对话');
  };

  return (
    <IOSPage className="flex flex-col h-full bg-[var(--color-bg-page)]">
      <IOSToaster />
      <IOSNavbar
        title="对话"
        right={
          <button
            type="button"
            onClick={handleNewChat}
            className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-accent)] text-white"
            aria-label="新建对话"
          >
            <Plus size={18} />
          </button>
        }
      />
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex gap-2 max-w-[85%]',
              msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''
            )}
          >
            {msg.sender === 'agent' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--color-accent)] flex items-center justify-center">
                <Bot size={16} className="text-white" />
              </div>
            )}
            <div className={cn(msg.sender === 'user' ? 'ml-auto' : '')}>
              <div className="flex items-center gap-2 mb-1">
                <span className="ios-footnote">{msg.name}</span>
                <span className="ios-footnote text-[var(--color-text-muted)]">{msg.time}</span>
              </div>
              <div className="ios-card rounded-[18px] px-4 py-3">
                <p className="text-[15px] leading-relaxed text-[var(--color-text-primary)]">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="sticky bottom-0 bg-[var(--color-bg-page)] border-t border-[var(--color-border-default)] px-4 py-3">
        <form onSubmit={handleSend} className="flex items-center gap-2">
          <button
            type="button"
            className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            aria-label="添加附件"
          >
            <Paperclip size={20} />
          </button>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="输入消息..."
            className="flex-1 h-10 px-4 rounded-full bg-[var(--color-bg-surface-2)] border border-[var(--color-border-default)] text-[15px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[var(--color-accent)] transition-colors"
          />
          <button
            type="submit"
            disabled={!inputValue.trim()}
            className={cn(
              'flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-full transition-colors',
              inputValue.trim()
                ? 'bg-[var(--color-accent)] text-white'
                : 'bg-[var(--color-bg-surface-3)] text-[var(--color-text-muted)]'
            )}
            aria-label="发送消息"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </IOSPage>
  );
}
