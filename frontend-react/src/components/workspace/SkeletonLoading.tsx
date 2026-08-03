import { Loader2 } from 'lucide-react';

export function SkeletonPulse({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2.5 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3 rounded-full skeleton-shimmer"
          style={{
            width: `${60 + Math.random() * 35}%`,
            animationDelay: `${i * 100}ms`,
          }}
        />
      ))}
    </div>
  );
}

export function ToolSkeleton({ toolName }: { toolName?: string }) {
  return (
    <div className="max-w-[85%] tool-call-card">
      <div className="tool-call-header">
        <div className="flex items-center gap-2 flex-1">
          <Loader2 size={13} style={{ color: 'var(--color-accent)' }} className="animate-spin" />
          <span className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>{toolName || 'Executing...'}</span>
        </div>
        <div className="flex gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-accent)' }} />
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-accent)', animationDelay: '200ms' }} />
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-accent)', animationDelay: '400ms' }} />
        </div>
      </div>
      <div className="p-3">
        <SkeletonPulse lines={2} />
      </div>
    </div>
  );
}

export function MessageSkeleton() {
  return (
    <div className="max-w-[80%] rounded-2xl rounded-tl-md p-4 message-enter" style={{
      backgroundColor: 'var(--color-bg-surface-2)',
      border: '1px solid var(--color-border-subtle)',
    }}>
      <SkeletonPulse lines={3} />
    </div>
  );
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl skeleton-shimmer" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-24 rounded-full skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
            <div className="h-2 w-40 rounded-full skeleton-shimmer" style={{ animationDelay: `${i * 100 + 50}ms` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <div className="w-16 h-16 rounded-3xl flex items-center justify-center mb-6 skeleton-shimmer" style={{
        background: 'linear-gradient(135deg, var(--color-accent-subtle), var(--color-accent-glow))',
      }} />
      <div className="w-48 h-4 rounded-full skeleton-shimmer mb-3" />
      <div className="w-64 h-3 rounded-full skeleton-shimmer" style={{ animationDelay: '100ms' }} />
    </div>
  );
}
