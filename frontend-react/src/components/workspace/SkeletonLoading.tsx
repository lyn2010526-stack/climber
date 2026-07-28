import { Loader2 } from 'lucide-react';

export function SkeletonPulse({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3 bg-gray-700 rounded animate-pulse"
          style={{
            width: `${70 + Math.random() * 30}%`,
            animationDelay: `${i * 150}ms`,
            animationDuration: '1.5s',
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
          <Loader2 size={13} className="text-blue-400 animate-spin" />
          <span className="text-xs font-medium text-gray-100">{toolName || 'Executing...'}</span>
        </div>
        <div className="flex gap-1.5">
          <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" />
          <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '200ms' }} />
          <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '400ms' }} />
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
    <div className="max-w-[80%] bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-md p-4">
      <SkeletonPulse lines={3} />
    </div>
  );
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-700 rounded-lg animate-pulse" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-24 bg-gray-700 rounded animate-pulse" />
            <div className="h-2 w-40 bg-gray-700 rounded animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}
