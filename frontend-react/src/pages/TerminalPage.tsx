import { TerminalPanel } from '../components/terminal/TerminalPanel';
import { PageHeader } from '../components/ui/PageHeader';
import { TerminalSquare } from 'lucide-react';
import { api } from '../api';
import { useI18n } from '../i18n';

const prompt = (text: string): string => `\x1b[37m${text}\x1b[0m`;

export default function TerminalPage() {
  const { t } = useI18n();
  const handleCommand = async (command: string): Promise<string> => {
    if (!command) return '';
    if (command === 'clear') return '\x1b[2J\x1b[H';
    try {
      const res = await api.executeSandboxCommand(command);
      const out = (res.output ?? '').replace(/\n/g, '\r\n');
      return res.success ? prompt(out) : `\x1b[31m${out}\x1b[0m`;
    } catch (err: any) {
      return `\x1b[31m${String(err?.message ?? err)}\x1b[0m`;
    }
  };

  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col page-transition">
      <div className="px-4 py-3 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
        <PageHeader
          title={t('terminal.title', { defaultValue: 'Sandbox terminal' })}
          description={t('terminal.subtitle', { defaultValue: 'Run commands through the sandbox API and view the output.' })}
          icon={<TerminalSquare size={20} />}
        />
      </div>
      <div className="flex-1 min-h-0 p-3 overflow-hidden">
        <TerminalPanel onCommand={handleCommand} className="h-full" />
      </div>
    </div>
  );
}
