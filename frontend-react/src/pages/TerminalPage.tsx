import { TerminalPanel } from '../components/terminal/TerminalPanel';
import { PageHeader } from '../components/ui/PageHeader';
import { TerminalSquare } from 'lucide-react';

export default function TerminalPage() {
  const handleCommand = (command: string) => {
    console.log('Terminal command:', command);
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
