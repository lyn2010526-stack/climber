import { useState, useEffect, useCallback } from 'react';
import { Eye, Shield, Zap, RefreshCw } from 'lucide-react';
import { api } from '../../api';

export type EngineMode = 'plan' | 'default' | 'auto';

const MODES: { id: EngineMode; label: string; description: string; icon: typeof Eye }[] = [
  { id: 'plan', label: '计划', description: '只读预览，不写文件、不执行命令', icon: Eye },
  { id: 'default', label: '手动', description: '写操作逐次确认', icon: Shield },
  { id: 'auto', label: '自动', description: '低风险自动执行，高风险需确认', icon: Zap },
];

function normalizeMode(value: string | undefined): EngineMode {
  if (value === 'plan') return 'plan';
  if (value === 'auto') return 'auto';
  return 'default';
}

export function EnginePermissionModeToggle() {
  const [mode, setMode] = useState<EngineMode>('default');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchMode = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const cfg = await api.getPermissionConfig();
      setMode(normalizeMode(cfg?.mode));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMode();
  }, [fetchMode]);

  const handleSelect = useCallback(async (next: EngineMode) => {
    if (next === mode || saving) return;
    setSaving(true);
    try {
      await api.updatePermissionConfig({ mode: next });
      setMode(next);
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  }, [mode, saving]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-2">
        <div className="w-4 h-4 border-2 rounded-full animate-spin" style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-between py-1">
        <span className="text-xs" style={{ color: 'var(--color-error)' }}>加载失败</span>
        <button onClick={fetchMode} className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-accent)' }}>
          <RefreshCw size={11} /> 重试
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 rounded-lg p-0.5" style={{ backgroundColor: 'var(--color-bg-surface-2)' }}>
      {MODES.map(({ id, label, description, icon: Icon }) => {
        const isActive = mode === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => handleSelect(id)}
            disabled={saving}
            title={description}
            aria-pressed={isActive}
            className="flex flex-1 flex-col items-center gap-0.5 rounded-md px-1 py-1.5 text-[10px] font-medium transition-all duration-200 disabled:opacity-50"
            style={{
              color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)',
              backgroundColor: isActive ? 'var(--color-accent-subtle)' : 'transparent',
            }}
          >
            <Icon size={13} strokeWidth={isActive ? 2.5 : 2} />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
