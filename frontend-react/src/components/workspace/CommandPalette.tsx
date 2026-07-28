import { useState, useEffect, useCallback } from 'react';
import {
  Search, Bot, Pause, Square, Camera, RotateCcw,
  Settings, Zap, Brain, GitBranch, Activity, FolderTree,
  Trash2, Archive, Download, Upload,
} from 'lucide-react';

interface Command {
  id: string;
  label: string;
  description?: string;
  icon?: any;
  shortcut?: string;
  category: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  commands: Command[];
}

export function CommandPalette({ isOpen, onClose, commands }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filtered = commands.filter(cmd =>
    !query ||
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    cmd.description?.toLowerCase().includes(query.toLowerCase()) ||
    cmd.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      filtered[selectedIndex].action();
      onClose();
    }
  }, [filtered, selectedIndex, onClose]);

  if (!isOpen) return null;

  const grouped = filtered.reduce((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = [];
    acc[cmd.category]!.push(cmd);
    return acc;
  }, {} as Record<string, Command[]>);

  let flatIndex = -1;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700">
          <Search size={16} className="text-gray-500" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
             placeholder="输入命令..."
            className="flex-1 bg-transparent text-sm text-gray-100 placeholder:text-gray-500 focus:outline-none"
            autoFocus
          />
          <kbd className="px-1.5 py-0.5 bg-gray-700 text-gray-500 text-[10px] rounded">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-1">
          {Object.entries(grouped).map(([category, cmds]) => (
            <div key={category}>
              <div className="px-4 py-1.5">
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                  {category}
                </span>
              </div>
              {cmds.map(cmd => {
                flatIndex++;
                const idx = flatIndex;
                return (
                  <button
                    key={cmd.id}
                    onClick={() => { cmd.action(); onClose(); }}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${
                      idx === selectedIndex ? 'bg-blue-600/10 text-blue-400' : 'text-gray-400 hover:bg-gray-700/50'
                    }`}
                  >
                    {cmd.icon && <cmd.icon size={14} />}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm">{cmd.label}</span>
                      {cmd.description && (
                        <span className="text-xs text-gray-500 ml-2 truncate">{cmd.description}</span>
                      )}
                    </div>
                    {cmd.shortcut && (
                      <kbd className="px-1.5 py-0.5 bg-gray-700 text-gray-500 text-[10px] rounded">
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-gray-500 text-sm">
              No commands found
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Default Commands Factory ──────────────────────────────────────────────

export function createDefaultCommands(actions: {
  onNewSession: () => void;
  onPause: () => void;
  onStop: () => void;
  onSnapshot: () => void;
  onRollback: () => void;
  onClearContext: () => void;
  onToggleExpertMode: () => void;
  onToggleFocusMode: () => void;
  onExportConfig: () => void;
  onImportConfig: () => void;
  onOpenSettings: () => void;
  onOpenSkills: () => void;
  onOpenMCP: () => void;
  onOpenTrace: () => void;
  onOpenFiles: () => void;
}): Command[] {
  return [
    { id: 'new-session', label: 'New Session', icon: Bot, shortcut: 'Ctrl+N', category: 'Session', action: actions.onNewSession },
    { id: 'pause', label: 'Pause Task', icon: Pause, category: 'Runtime', action: actions.onPause },
    { id: 'stop', label: 'Stop Task', icon: Square, category: 'Runtime', action: actions.onStop },
    { id: 'snapshot', label: 'Save Snapshot', icon: Camera, shortcut: 'Ctrl+Shift+S', category: 'Runtime', action: actions.onSnapshot },
    { id: 'rollback', label: 'Rollback to Snapshot', icon: RotateCcw, category: 'Runtime', action: actions.onRollback },
    { id: 'clear-context', label: 'Clear Context & Archive', icon: Trash2, shortcut: 'Ctrl+K', category: 'Session', action: actions.onClearContext },
    { id: 'expert-mode', label: 'Toggle Expert Mode', icon: Activity, category: 'View', action: actions.onToggleExpertMode },
    { id: 'focus-mode', label: 'Toggle Focus Mode', icon: Archive, category: 'View', action: actions.onToggleFocusMode },
    { id: 'skills', label: 'Open Skills', icon: Brain, category: 'Panels', action: actions.onOpenSkills },
    { id: 'mcp', label: 'Open MCP Panel', icon: Zap, category: 'Panels', action: actions.onOpenMCP },
    { id: 'trace', label: 'Open Trace', icon: GitBranch, category: 'Panels', action: actions.onOpenTrace },
    { id: 'files', label: 'Open Files', icon: FolderTree, category: 'Panels', action: actions.onOpenFiles },
    { id: 'export', label: 'Export Config', icon: Download, category: 'Config', action: actions.onExportConfig },
    { id: 'import', label: 'Import Config', icon: Upload, category: 'Config', action: actions.onImportConfig },
    { id: 'settings', label: 'Settings', icon: Settings, category: 'Config', action: actions.onOpenSettings },
  ];
}
