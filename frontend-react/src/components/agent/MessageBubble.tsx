import React from 'react';
import { cn } from '../../lib/utils';
import { User, Bot, Wrench, AlertCircle } from 'lucide-react';

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

interface MessageBubbleProps {
  role: MessageRole;
  content: string;
  toolCalls?: Array<{
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    result?: string;
    error?: string;
  }>;
  reasoning?: string;
  timestamp?: Date;
  className?: string;
}

const roleConfig = {
  user: {
    icon: User,
    bg: 'bg-accent/10 border-accent/20',
    align: 'ml-auto',
    label: 'You',
  },
  assistant: {
    icon: Bot,
    bg: 'bg-surface-raised border-border',
    align: 'mr-auto',
    label: 'Climber',
  },
  system: {
    icon: AlertCircle,
    bg: 'bg-warning/10 border-warning/20',
    align: 'mx-auto',
    label: 'System',
  },
  tool: {
    icon: Wrench,
    bg: 'bg-info/10 border-info/20',
    align: 'mr-auto',
    label: 'Tool',
  },
};

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  content,
  toolCalls,
  reasoning,
  timestamp,
  className,
}) => {
  const config = roleConfig[role] || roleConfig.assistant;
  const Icon = config.icon;

  return (
    <div className={cn('flex gap-3 max-w-[85%]', config.align, className)}>
      <div className={cn('flex-shrink-0 w-8 h-8 rounded-lg border flex items-center justify-center', config.bg)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">{config.label}</span>
          {timestamp && <span className="text-xs text-muted-foreground/60">{timestamp.toLocaleTimeString()}</span>}
        </div>
        <div className={cn('rounded-xl border px-4 py-3', config.bg)}>
          {reasoning && (
            <details className="mb-2">
              <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                Reasoning
              </summary>
              <div className="mt-2 p-2 rounded-lg bg-surface-inset text-xs text-muted-foreground font-mono whitespace-pre-wrap">
                {reasoning}
              </div>
            </details>
          )}
          <div className="text-sm leading-relaxed whitespace-pre-wrap">{content}</div>
        </div>
        {toolCalls && toolCalls.length > 0 && (
          <div className="space-y-2">
            {toolCalls.map((tool) => (
              <div key={tool.id} className="rounded-lg border border-border bg-surface-inset p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Wrench className="h-3.5 w-3.5 text-info" />
                  <span className="text-xs font-medium text-foreground">{tool.name}</span>
                </div>
                <div className="text-xs text-muted-foreground font-mono mb-2">
                  {JSON.stringify(tool.arguments, null, 2)}
                </div>
                {tool.error ? (
                  <div className="flex items-center gap-1.5 text-xs text-destructive">
                    <AlertCircle className="h-3 w-3" />
                    {tool.error}
                  </div>
                ) : tool.result && (
                  <div className="text-xs text-muted-foreground bg-surface-base p-2 rounded border border-border/50">
                    {tool.result}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
