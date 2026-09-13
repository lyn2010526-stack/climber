import { TerminalPanel } from '../components/terminal/TerminalPanel';
import { PageHeader } from '../components/ui/PageHeader';
import { TerminalSquare } from 'lucide-react';
import { api } from '../api';

const prompt = (text: string): string => `\x1b[37m${text}\x1b[0m`;

export default function TerminalPage() {
  const handleCommand = async (command: string): Promise<string> => {
    if (!command) return '';
    if (command === 'clear') return '\x1b[2J\x1b[H';
    try {
      const res = await api.executeSandboxCommand(command);
      const out = (res.output ?? '').replace(/\n/g, '\r\n');
      return res.success ? prompt(out) : `\x1b[31m${prompt(out)}\x1b[0m`;
    } catch (err: any) {
      return `\x1b[31m${String(err?.message ?? err)}\x1b[0m`;
    }
  };

  return (
    <div className="h-full flex flex-col page-transition">
      <div className="px-4 py-3 md:px-6 md:py-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/80 backdrop-blur-xl">
        <PageHeader
          title="终端沙箱"
          description="安全的命令执行环境"
          icon={<TerminalSquare size={20} />}
        />
      </div>
      <div className="flex-1 p-4 overflow-hidden">
        <TerminalPanel onCommand={handleCommand} className="h-full" />
      </div>
    </div>
  );
}
