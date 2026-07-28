import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench, CheckCircle2, XCircle } from 'lucide-react';

interface ToolCallCardProps {
  toolName: string;
  args: Record<string, unknown>;
  result?: string;
  success?: boolean;
}

export function ToolCallCard({ toolName, args, result, success }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-1.5 rounded-lg border border-blue-500/20 bg-blue-600/5 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-left hover:bg-blue-600/5 transition-colors"
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        <Wrench size={10} className="text-blue-400" />
        <span className="text-[10px] font-medium text-blue-400">{toolName}</span>
        {success !== undefined && (
          success
            ? <CheckCircle2 size={10} className="text-green-400 ml-auto" />
            : <XCircle size={10} className="text-red-400 ml-auto" />
        )}
      </button>

      {expanded && (
        <div className="px-2 pb-2 space-y-1.5 border-t border-blue-500/10">
          <div>
            <span className="text-[9px] text-gray-500 font-medium">参数:</span>
            <pre className="text-[9px] text-gray-400 bg-gray-700 rounded p-1 mt-0.5 overflow-x-auto">
              {JSON.stringify(args, null, 2).slice(0, 300)}
            </pre>
          </div>
          {result && (
            <div>
              <span className="text-[9px] text-gray-500 font-medium">结果:</span>
              <pre className="text-[9px] text-gray-400 bg-gray-700 rounded p-1 mt-0.5 overflow-x-auto max-h-20">
                {result.slice(0, 500)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
