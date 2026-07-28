import { TerminalPanel } from '../components/terminal/TerminalPanel';

export default function TerminalPage() {
  const handleCommand = (command: string) => {
    console.log('Terminal command:', command);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-white/5 bg-[#0F0F14]">
        <h2 className="text-sm font-semibold text-white">终端沙箱</h2>
        <p className="text-xs text-gray-500">安全的命令执行环境</p>
      </div>
      <div className="flex-1 p-4">
        <TerminalPanel onCommand={handleCommand} className="h-full" />
      </div>
    </div>
  );
}
