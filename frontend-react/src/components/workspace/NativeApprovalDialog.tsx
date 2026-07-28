import { useEffect, useCallback } from 'react';
import { Terminal, AlertTriangle, FolderOpen } from 'lucide-react';

interface NativeApprovalDialogProps {
  isOpen: boolean;
  command: string;
  riskLevel: 'low' | 'medium' | 'high';
  cwd?: string;
  onAllow: () => void;
  onAllowAlways: () => void;
  onDeny: () => void;
}

const riskConfig = {
  low: {
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    badge: 'bg-emerald-500/15 text-emerald-400',
    glow: 'shadow-emerald-500/10',
  },
  medium: {
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    badge: 'bg-amber-500/15 text-amber-400',
    glow: 'shadow-amber-500/10',
  },
  high: {
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    badge: 'bg-red-500/15 text-red-400',
    glow: 'shadow-red-500/10',
  },
};

export function NativeApprovalDialog({
  isOpen,
  command,
  riskLevel,
  cwd,
  onAllow,
  onAllowAlways,
  onDeny,
}: NativeApprovalDialogProps) {
  const config = riskConfig[riskLevel];

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!isOpen) return;
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

    switch (e.key.toLowerCase()) {
      case 'y':
        e.preventDefault();
        onAllow();
        break;
      case 'n':
        e.preventDefault();
        onDeny();
        break;
      case 'a':
        e.preventDefault();
        onAllowAlways();
        break;
    }
  }, [isOpen, onAllow, onDeny, onAllowAlways]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onDeny}
      />

      <div className={`relative w-full max-w-[500px] mx-4 bg-gray-900 border ${config.border} rounded-xl shadow-xl ${config.glow} overflow-hidden animate-scaleIn`}>
        <div className={`flex items-center gap-2.5 px-5 py-3.5 ${config.bg}`}>
          <AlertTriangle size={16} className={config.color} />
          <h3 className="text-sm font-medium text-gray-100">Approve Command Execution</h3>
          <span className={`ml-auto px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${config.badge}`}>
            {riskLevel}
          </span>
        </div>

        <div className="px-5 py-4 space-y-3">
          <div className="flex items-start gap-2">
            <Terminal size={13} className="text-gray-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
               <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">命令</p>
              <pre className="code-block text-xs leading-relaxed break-all whitespace-pre-wrap max-h-32 overflow-y-auto">
                {command}
              </pre>
            </div>
          </div>

          {cwd && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <FolderOpen size={13} className="text-gray-500 shrink-0" />
               <span className="text-gray-500">工作目录：</span>
              <span className="font-mono text-gray-400 truncate">{cwd}</span>
            </div>
          )}
        </div>

        <div className="px-5 py-3.5 border-t border-gray-700 bg-gray-800">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onAllow}
              className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-medium rounded-lg hover:bg-emerald-500/20 transition-colors"
            >
               允许一次
              <kbd className="ml-1 px-1 py-0.5 bg-emerald-500/10 rounded text-[9px] font-mono">Y</kbd>
            </button>

            <button
              type="button"
              onClick={onAllowAlways}
              className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-blue-600/10 border border-blue-500/25 text-blue-400 text-xs font-medium rounded-lg hover:bg-blue-600/20 transition-colors"
            >
               始终允许
              <kbd className="ml-1 px-1 py-0.5 bg-blue-600/10 rounded text-[9px] font-mono">A</kbd>
            </button>

            <button
              type="button"
              onClick={onDeny}
              className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-medium rounded-lg hover:bg-red-500/20 transition-colors"
            >
               拒绝
              <kbd className="ml-1 px-1 py-0.5 bg-red-500/10 rounded text-[9px] font-mono">N</kbd>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
