import { useState, useCallback, useEffect } from 'react';
import { Shield, Globe } from 'lucide-react';

interface PermissionModeToggleProps {
  value: 'sandbox' | 'native';
  onChange: (mode: 'sandbox' | 'native') => void;
}

const STORAGE_KEY = 'agent-engine-permission-mode';

export function PermissionModeToggle({ value, onChange }: PermissionModeToggleProps) {
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  useEffect(() => {
    if (value) {
      localStorage.setItem(STORAGE_KEY, value);
    }
  }, [value]);

  const handleToggle = useCallback((mode: 'sandbox' | 'native') => {
    if (mode === value) return;

    if (mode === 'native') {
      setToastMessage('已启用原生模式 — 智能体拥有完整系统访问权限');
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    }

    onChange(mode);
  }, [value, onChange]);

  return (
    <div className="relative inline-flex items-center">
      <div className="flex items-center bg-gray-800 border border-gray-700 rounded-lg p-0.5">
        <button
          type="button"
          onClick={() => handleToggle('sandbox')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
            value === 'sandbox'
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/10'
              : 'text-gray-400 hover:text-gray-100 hover:bg-gray-700/50'
          }`}
          title="沙箱模式 — 安全受限环境"
        >
          <Shield size={13} />
          <span>沙箱</span>
        </button>

        <button
          type="button"
          onClick={() => handleToggle('native')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
            value === 'native'
              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 shadow-sm shadow-amber-500/10'
              : 'text-gray-400 hover:text-gray-100 hover:bg-gray-700/50'
          }`}
          title="原生模式 — 完整系统访问，需要审批"
        >
          <Globe size={13} />
          <span>原生</span>
        </button>
      </div>

      {showToast && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50 animate-slideUp">
          <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs px-3 py-2 rounded-lg whitespace-nowrap shadow-lg shadow-amber-500/5">
            {toastMessage}
          </div>
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45 bg-amber-500/10 border-l border-t border-amber-500/30" />
        </div>
      )}
    </div>
  );
}

export function getStoredPermissionMode(): 'sandbox' | 'native' {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'native' ? 'native' : 'sandbox';
}
