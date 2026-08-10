import { useCallback, useRef } from 'react';
import { TerminalPanel, type TerminalPanelHandle } from '../components/terminal/TerminalPanel';
import { api } from '../api';

export default function TerminalPage() {
  const termRef = useRef<TerminalPanelHandle>(null);

  const handleCommand = useCallback(async (command: string) => {
    if (!command) return;
    try {
      const res = await api.executeCommand(command, 30);
      const output = res?.output || '命令已完成（无输出）';
      termRef.current?.appendOutput(output);
    } catch (e: any) {
      termRef.current?.appendOutput(`错误: ${e?.message || String(e)}`);
    }
  }, []);

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">终端沙箱</h2>
        <p className="text-xs text-[var(--color-text-muted)]">安全的命令执行环境</p>
      </div>
      <div className="flex-1 p-4">
        <TerminalPanel ref={termRef} onCommand={handleCommand} className="h-full" />
      </div>
    </div>
  );
}
