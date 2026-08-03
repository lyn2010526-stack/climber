import { Brain, Wrench, Globe, FileText } from 'lucide-react';

interface StreamingIndicatorProps {
  text?: string;
  type?: 'thinking' | 'tool' | 'browser' | 'file';
}

const typeConfig: Record<NonNullable<StreamingIndicatorProps['type']>, { icon: typeof Brain; defaultText: string }> = {
  thinking: { icon: Brain, defaultText: 'Thinking...' },
  tool: { icon: Wrench, defaultText: 'Running tool...' },
  browser: { icon: Globe, defaultText: 'Navigating...' },
  file: { icon: FileText, defaultText: 'Reading file...' },
};

function WaveformBars() {
  return (
    <div className="flex items-end gap-[2px] h-3">
      {[0, 1, 2, 3, 4].map(i => (
        <span
          key={i}
          className="w-[3px] bg-blue-400 rounded-full"
          style={{
            animation: 'streamingBar 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.15}s`,
            height: '100%',
          }}
        />
      ))}
    </div>
  );
}

export function StreamingIndicator({ text, type = 'thinking' }: StreamingIndicatorProps) {
  const config = typeConfig[type];
  const Icon = config.icon;
  const displayText = text || config.defaultText;

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-lg">
      <WaveformBars />
      <Icon size={12} className="text-blue-400" />
      <span className="text-xs text-[var(--color-text-primary)] font-medium">{displayText}</span>
      <style>{`
        @keyframes streamingBar {
          0%, 100% { transform: scaleY(0.4); opacity: 0.5; }
          50% { transform: scaleY(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
