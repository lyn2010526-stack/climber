import { useState } from 'react';
import {
  AlertTriangle, Check, X, Edit3, Shield,
} from 'lucide-react';

interface ApprovalCardProps {
  toolName: string;
  command?: string;
  reason: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  onApprove: (modifiedParams?: any) => void;
  onDeny: () => void;
  onModify: (newParams: any) => void;
}

export function InlineApprovalCard({
  toolName,
  command,
  reason,
  riskLevel,
  onApprove,
  onDeny,
  onModify,
}: ApprovalCardProps) {
  const [editing, setEditing] = useState(false);
  const [modifiedCommand, setModifiedCommand] = useState(command || '');

  const riskColors: Record<string, string> = {
    low: 'border-blue-500/20 bg-blue-600/5',
    medium: 'border-amber-500/20 bg-amber-500/5',
    high: 'border-red-500/20 bg-red-500/5',
    critical: 'border-red-500/40 bg-red-500/10',
  };

  const riskIconColors: Record<string, string> = {
    low: 'text-blue-400',
    medium: 'text-amber-400',
    high: 'text-red-400',
    critical: 'text-red-400',
  };

  return (
    <div className={`max-w-[85%] rounded-xl border ${riskColors[riskLevel]} overflow-hidden`}>
      <div className="flex items-center gap-2 px-4 py-2.5">
        <AlertTriangle size={14} className={riskIconColors[riskLevel]} />
         <span className="text-xs font-medium text-[var(--color-text-primary)]">需要批准</span>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium capitalize ${
          riskLevel === 'critical' ? 'bg-red-500/20 text-red-400' :
          riskLevel === 'high' ? 'bg-red-500/10 text-red-400' :
          riskLevel === 'medium' ? 'bg-amber-500/10 text-amber-400' :
          'bg-blue-600/10 text-blue-400'
        }`}>
          {riskLevel}
        </span>
      </div>

      <div className="px-4 pb-2 space-y-1">
        <div className="flex items-center gap-2 text-xs">
          <Shield size={11} className="text-[var(--color-text-muted)]" />
          <span className="text-[var(--color-text-secondary)]">{toolName}</span>
        </div>
        <p className="text-[10px] text-[var(--color-text-muted)]">{reason}</p>
        {command && !editing && (
          <pre className="code-block text-[10px] mt-1 max-h-20 overflow-y-auto">{command}</pre>
        )}
        {editing && (
          <textarea
            value={modifiedCommand}
            onChange={(e) => setModifiedCommand(e.target.value)}
            className="w-full h-16 px-2 py-1 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] rounded text-[10px] text-[var(--color-text-primary)] font-mono resize-none focus:outline-none focus:border-[var(--color-accent)]/50"
          />
        )}
      </div>

      <div className="flex items-center gap-2 px-4 py-2.5 border-t border-[var(--color-border-subtle)]/50">
        <button
          onClick={() => onApprove()}
          className="flex items-center gap-1 px-3 py-1 text-[10px] bg-green-500/10 text-green-400 rounded-lg hover:bg-green-500/20"
        >
          <Check size={10} /> Allow
        </button>
        <button
          onClick={() => onDeny()}
          className="flex items-center gap-1 px-3 py-1 text-[10px] bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20"
        >
          <X size={10} /> Deny
        </button>
        {command && (
          <button
            onClick={() => {
              if (editing) {
                onModify({ command: modifiedCommand });
              } else {
                setEditing(true);
              }
            }}
            className="flex items-center gap-1 px-3 py-1 text-[10px] bg-blue-600/10 text-blue-400 rounded-lg hover:bg-blue-600/20"
          >
            <Edit3 size={10} /> {editing ? 'Apply' : 'Modify'}
          </button>
        )}
      </div>
    </div>
  );
}
