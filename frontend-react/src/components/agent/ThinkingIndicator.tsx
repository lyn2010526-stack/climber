import { useEffect, useState } from 'react';
import { Brain, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ThinkingIndicatorProps {
  /** Current thinking stage text */
  stage?: string;
  /** Whether thinking is active */
  isActive?: boolean;
  /** Compact mode for inline display */
  compact?: boolean;
  /** Show sparkle animation */
  sparkle?: boolean;
  className?: string;
}

const thinkingStages = [
  '正在分析问题...',
  '正在规划方案...',
  '正在推理...',
  '正在整合信息...',
  '即将完成...',
];

export function ThinkingIndicator({
  stage,
  isActive = true,
  compact = false,
  sparkle = false,
  className,
}: ThinkingIndicatorProps) {
  // One 200ms tick drives dots (400ms), stage rotation (3s) and sparkle (4s on / 1s off).
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!isActive) return;

    const tickInterval = setInterval(() => {
      setTick(prev => prev + 1);
    }, 200);

    return () => clearInterval(tickInterval);
  }, [isActive]);

  if (!isActive) return null;

  const dots = '.'.repeat(Math.floor(tick / 2) % 4);
  const currentStage = Math.floor(tick / 15) % thinkingStages.length;
  const showSparkle = tick >= 20 && tick % 20 < 5;

  const displayText = stage || thinkingStages[currentStage];

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className="relative">
          <Brain size={14} className="text-blue-400" />
          <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
        </div>
        <span className="text-xs text-blue-400/80">
          {displayText}{dots}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-xl border border-blue-500/10 bg-blue-500/[0.03]',
        'animate-[fadeIn_0.3s_ease_forwards]',
        className
      )}
    >
      {/* Animated icon */}
      <div className="relative shrink-0">
        <div className="p-2 rounded-xl bg-blue-500/10">
          <Brain size={16} className="text-blue-400" />
        </div>
        {sparkle && (
          <Sparkles
            size={12}
            className={cn(
              'absolute -top-1 -right-1 text-yellow-400 transition-opacity duration-300',
              showSparkle ? 'opacity-100' : 'opacity-0'
            )}
          />
        )}
        {/* Pulsing ring */}
        <div className="absolute inset-0 rounded-xl border border-blue-400/30 animate-ping opacity-30" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-blue-400">思考中</span>
          <div className="flex gap-1">
            <span
              className="w-1 h-1 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: '0ms' }}
            />
            <span
              className="w-1 h-1 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: '150ms' }}
            />
            <span
              className="w-1 h-1 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: '300ms' }}
            />
          </div>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          {displayText}{stage ? dots : ''}
        </p>

        {/* Subtle progress bar */}
        <div className="mt-3 h-0.5 bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-violet-500 rounded-full animate-[progress_2s_ease-in-out_infinite]"
            style={{ width: '60%' }}
          />
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes progress {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(0%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}

/** Minimal inline "thinking..." indicator for message bubbles */
export function ThinkingDots({ text }: { text?: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary)]">
      <Brain size={13} className="text-blue-400/70" />
      {text || '思考中'}
      {/* CSS-driven dots avoid a setInterval per mounted bubble. */}
      <span className="thinking-dots" aria-hidden="true" />
      <style>{`
        @keyframes thinkingDots {
          0%, 24.99% { content: ''; }
          25%, 49.99% { content: '.'; }
          50%, 74.99% { content: '..'; }
          75%, 100% { content: '...'; }
        }
        .thinking-dots::after {
          content: '';
          display: inline-block;
          min-width: 1.2em;
          text-align: left;
          animation: thinkingDots 1.6s infinite;
        }
      `}</style>
    </span>
  );
}
