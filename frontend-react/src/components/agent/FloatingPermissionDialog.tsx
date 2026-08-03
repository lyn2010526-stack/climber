import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Check, X, FileText, Terminal, Globe } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

export interface PermissionRequest {
  id: string;
  action: 'file_read' | 'file_write' | 'file_delete' | 'command' | 'network' | 'mcp_tool';
  description: string;
  details?: string;
  severity: 'low' | 'medium' | 'high';
  timestamp: number;
}

interface FloatingPermissionDialogProps {
  requests: PermissionRequest[];
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
  onApproveAll: () => void;
}

const actionConfig = {
  file_read: { icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10', label: '读取文件' },
  file_write: { icon: FileText, color: 'text-amber-400', bg: 'bg-amber-500/10', label: '修改文件' },
  file_delete: { icon: FileText, color: 'text-red-400', bg: 'bg-red-500/10', label: '删除文件' },
  command: { icon: Terminal, color: 'text-orange-400', bg: 'bg-orange-500/10', label: '执行命令' },
  network: { icon: Globe, color: 'text-purple-400', bg: 'bg-purple-500/10', label: '网络访问' },
  mcp_tool: { icon: Terminal, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'MCP 工具' },
};

const severityConfig = {
  low: { border: 'border-blue-500/30', glow: '' },
  medium: { border: 'border-amber-500/30', glow: 'shadow-amber-500/10' },
  high: { border: 'border-red-500/30', glow: 'shadow-red-500/20' },
};

export function FloatingPermissionDialog({
  requests,
  onApprove,
  onDeny,
  onApproveAll,
}: FloatingPermissionDialogProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (requests.length > 0) {
      setVisible(true);
    }
  }, [requests]);

  if (!visible || requests.length === 0) return null;

  const latestRequest = requests[requests.length - 1]!;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pointer-events-none">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-[2px] pointer-events-auto" />

      <div
        className={cn(
          'relative w-full max-w-lg mx-4 mb-4 pointer-events-auto',
          'transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
          'animate-[slideUp_0.3s_ease_forwards]'
        )}
        style={{
          animation: 'slideUp 0.3s cubic-bezier(0.16,1,0.3,1) forwards',
        }}
      >
        <Card
          variant="glass"
          padding="none"
          className={cn(
            'overflow-hidden shadow-2xl',
            severityConfig[latestRequest.severity].glow,
            severityConfig[latestRequest.severity].border
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-amber-400" />
              <span className="text-sm font-semibold text-white">权限请求</span>
              {requests.length > 1 && (
                <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-amber-500/10 text-amber-400 font-medium">
                  {requests.length} 个待处理
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              {requests.length > 1 && (
                <Button variant="ghost" size="sm" onClick={onApproveAll}>
                  全部允许
                </Button>
              )}
              <button
                onClick={() => { setVisible(false); }}
                className="p-1 rounded-lg hover:bg-white/[0.06] text-[var(--color-text-secondary)] transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* Request list */}
          <div className="max-h-[300px] overflow-y-auto">
            {requests.map((req, index) => {
              const config = actionConfig[req.action];
              const isExpanded = expanded === req.id;
              const isLatest = index === requests.length - 1;

              return (
                <div
                  key={req.id}
                  className={cn(
                    'border-b border-white/[0.04] last:border-b-0',
                    isLatest ? 'bg-white/[0.02]' : 'bg-transparent'
                  )}
                >
                  <div
                    className="flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-white/[0.02] transition-colors"
                    onClick={() => setExpanded(isExpanded ? null : req.id)}
                  >
                    <div className={cn('p-2 rounded-xl', config.bg)}>
                      <config.icon size={14} className={config.color} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-[var(--color-text-primary)]">{config.label}</span>
                        {req.severity === 'high' && (
                          <AlertTriangle size={12} className="text-red-400" />
                        )}
                      </div>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 truncate">{req.description}</p>
                    </div>
                    {isLatest && (
                      <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-blue-500/10 text-blue-400 font-medium animate-pulse">
                        新请求
                      </span>
                    )}
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="px-4 pb-3 animate-[fadeIn_0.2s_ease_forwards]">
                      {req.details && (
                        <pre className="text-[11px] text-[var(--color-text-secondary)] font-mono bg-black/30 rounded-lg p-3 mb-3 overflow-x-auto whitespace-pre-wrap">
                          {req.details}
                        </pre>
                      )}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); onApprove(req.id); }}
                        >
                          <Check size={12} />
                          允许
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); onDeny(req.id); }}
                        >
                          <X size={12} />
                          拒绝
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Quick actions for latest request */}
          {requests.length === 1 && (
            <div className="flex items-center gap-2 px-4 py-3 border-t border-white/[0.06] bg-white/[0.01]">
              <Button
                variant="primary"
                size="sm"
                onClick={() => onApprove(latestRequest.id)}
                className="flex-1"
              >
                <Check size={14} />
                允许执行
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDeny(latestRequest.id)}
                className="flex-1"
              >
                <X size={14} />
                拒绝
              </Button>
            </div>
          )}
        </Card>
      </div>

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-5px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
