import { useState } from 'react';
import { FileText, Plus, Minus, ChevronDown, ChevronRight } from 'lucide-react';

interface DiffLine {
  type: 'added' | 'removed' | 'context';
  content: string;
  oldLine?: number;
  newLine?: number;
}

interface FileDiff {
  filename: string;
  status: 'added' | 'modified' | 'removed';
  diff: DiffLine[];
}

interface DiffViewProps {
  diffs: FileDiff[];
}

export function DiffView({ diffs }: DiffViewProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  const toggleFile = (filename: string) => {
    setExpandedFiles(prev => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return next;
    });
  };

  if (!diffs.length) {
    return (
      <div className="text-center py-8 text-gray-500 text-sm">
        No changes to display
      </div>
    );
  }

  const totalAdditions = diffs.reduce((sum, f) => sum + f.diff.filter(d => d.type === 'added').length, 0);
  const totalRemovals = diffs.reduce((sum, f) => sum + f.diff.filter(d => d.type === 'removed').length, 0);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs">
        <span className="text-green-400">+{totalAdditions}</span>
        <span className="text-red-400">-{totalRemovals}</span>
        <span className="text-gray-400">{diffs.length} files changed</span>
      </div>

      {diffs.map((file) => (
        <div key={file.filename} className="border border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleFile(file.filename)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-750 text-left"
          >
            {expandedFiles.has(file.filename) ? (
              <ChevronDown size={14} className="text-gray-400" />
            ) : (
              <ChevronRight size={14} className="text-gray-400" />
            )}
            <FileText size={14} className="text-gray-400" />
            <span className="text-xs font-medium text-gray-200 flex-1">{file.filename}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              file.status === 'added' ? 'bg-green-900/30 text-green-300' :
              file.status === 'removed' ? 'bg-red-900/30 text-red-300' :
              'bg-yellow-900/30 text-yellow-300'
            }`}>
              {file.status}
            </span>
          </button>

          {expandedFiles.has(file.filename) && (
            <div className="bg-gray-900 font-mono text-xs max-h-64 overflow-y-auto">
              {file.diff.map((line, idx) => (
                <div
                  key={idx}
                  className={`flex ${
                    line.type === 'added' ? 'bg-green-900/20' :
                    line.type === 'removed' ? 'bg-red-900/20' :
                    'bg-gray-900'
                  }`}
                >
                  <span className="w-12 shrink-0 text-right px-2 text-gray-600 select-none border-r border-gray-800">
                    {line.oldLine ?? line.newLine ?? ''}
                  </span>
                  <span className="w-12 shrink-0 text-right px-2 text-gray-600 select-none border-r border-gray-800">
                    {line.newLine ?? line.oldLine ?? ''}
                  </span>
                  <span className={`flex-1 px-2 ${
                    line.type === 'added' ? 'text-green-300' :
                    line.type === 'removed' ? 'text-red-300' :
                    'text-gray-400'
                  }`}>
                    {line.type === 'added' && <Plus size={12} className="inline mr-1" />}
                    {line.type === 'removed' && <Minus size={12} className="inline mr-1" />}
                    {line.content}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
