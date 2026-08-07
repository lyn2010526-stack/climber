import {
  Undo2, Redo2, Save, Play, Bug, Download, Upload,
  ZoomIn, ZoomOut, Maximize2, Trash2,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface WorkflowToolbarProps {
  workflowName: string;
  onNameChange: (name: string) => void;
  onSave: () => void;
  onRun: () => void;
  onDebug: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  onImport: () => void;
  onExport: () => void;
  onClear: () => void;
  saving: boolean;
  running: boolean;
  debugMode: boolean;
  canUndo: boolean;
  canRedo: boolean;
}

function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  disabled = false,
  active = false,
  variant = 'default',
}: {
  icon: any;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  variant?: 'default' | 'primary' | 'danger';
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium',
        'transition-all duration-150 whitespace-nowrap',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        variant === 'default' && !active && [
          'text-[var(--color-text-secondary)]',
          'hover:bg-[var(--color-bg-surface-elevated)] hover:text-[var(--color-text-primary)]',
          'active:scale-95',
        ],
        variant === 'primary' && [
          'bg-[var(--color-accent)] text-white',
          'hover:bg-[var(--color-accent-hover)]',
          'shadow-sm shadow-[var(--color-accent)]/20',
          'active:scale-95',
        ],
        variant === 'danger' && [
          'text-red-400 hover:bg-red-500/10',
          'active:scale-95',
        ],
        active && [
          'bg-[var(--color-accent)]/15 text-[var(--color-accent)]',
          'border border-[var(--color-accent)]/30',
        ],
      )}
    >
      <Icon size={13} />
      <span className="hidden xl:inline">{label}</span>
    </button>
  );
}

function ToolbarDivider() {
  return <div className="w-px h-5 bg-[var(--color-border-subtle)]" />;
}

export function WorkflowToolbar({
  workflowName,
  onNameChange,
  onSave,
  onRun,
  onDebug,
  onUndo,
  onRedo,
  onZoomIn,
  onZoomOut,
  onFitView,
  onImport,
  onExport,
  onClear,
  saving,
  running,
  debugMode,
  canUndo,
  canRedo,
}: WorkflowToolbarProps) {
  return (
    <div className="h-11 flex items-center px-3 gap-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]/80 backdrop-blur-sm">
      {/* Workflow Name */}
      <input
        type="text"
        value={workflowName}
        onChange={(e) => onNameChange(e.target.value)}
        className={cn(
          'text-[12px] font-semibold text-[var(--color-text-primary)]',
          'bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]/30',
          'rounded px-2 py-0.5 -ml-2 min-w-[140px] max-w-[200px]',
          'transition-all duration-150'
        )}
        placeholder="Workflow name..."
      />

      <ToolbarDivider />

      {/* History */}
      <ToolbarButton icon={Undo2} label="Undo" onClick={onUndo} disabled={!canUndo} />
      <ToolbarButton icon={Redo2} label="Redo" onClick={onRedo} disabled={!canRedo} />

      <ToolbarDivider />

      {/* Zoom Controls */}
      <ToolbarButton icon={ZoomOut} label="Zoom Out" onClick={onZoomOut} />
      <ToolbarButton icon={ZoomIn} label="Zoom In" onClick={onZoomIn} />
      <ToolbarButton icon={Maximize2} label="Fit View" onClick={onFitView} />

      <ToolbarDivider />

      {/* Import / Export */}
      <ToolbarButton icon={Upload} label="Import" onClick={onImport} />
      <ToolbarButton icon={Download} label="Export" onClick={onExport} />

      <div className="flex-1" />

      {/* Debug */}
      <ToolbarButton
        icon={Bug}
        label="Debug"
        onClick={onDebug}
        active={debugMode}
      />

      <ToolbarDivider />

      {/* Clear */}
      <ToolbarButton icon={Trash2} label="Clear" onClick={onClear} variant="danger" />

      {/* Save */}
      <ToolbarButton
        icon={Save}
        label={saving ? 'Saving...' : 'Save'}
        onClick={onSave}
        disabled={saving}
      />

      {/* Run */}
      <ToolbarButton
        icon={Play}
        label={running ? 'Running...' : 'Run'}
        onClick={onRun}
        disabled={running}
        variant="primary"
      />
    </div>
  );
}
