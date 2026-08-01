import React, { useEffect, useState } from 'react';
import { Brain, Lightbulb, Cpu, Sparkles } from 'lucide-react';
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
  const [dots, setDots] = useState('');
  const [currentStage, setCurrentStage] = useState(0);
  const [showSparkle, setShowSparkle] = useState(false);

  useEffect(() => {
    if (!isActive) return;

    const dotInterval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 400);

    return () => clearInterval(dotInterval);
  }, [isActive]);

  useEffect(() => {
    if (!isActive || stage) return;

    const stageInterval = setInterval(() => {
      setCurrentStage(prev => (prev + 1) % thinkingStages.length);
    }, 3000);

    return () => clearInterval(stageInterval);
  }, [isActive, stage]);

  useEffect(() => {
    if (!sparkle || !isActive) return;

    const sparkleInterval = setInterval(() => {
      setShowSparkle(true);
      setTimeout(() => setShowSparkle(false), 1000);
    }, 4000);

    return () => clearInterval(sparkleInterval);
  }, [sparkle, isActive]);

  if (!isActive) return null;

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
        <p className="text-sm text-gray-300 leading-relaxed">
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
  const [dots, setDots] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 400);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="inline-flex items-center gap-1 text-sm text-gray-400">
      <Brain size={13} className="text-blue-400/70" />
      {text || '思考中'}{dots}
    </span>
  );
}
