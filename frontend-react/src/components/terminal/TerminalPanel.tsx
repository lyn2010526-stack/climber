import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { cn } from '../../lib/utils';

export interface TerminalPanelHandle {
  appendOutput: (text: string) => void;
}

interface TerminalPanelProps {
  onCommand?: (command: string) => void;
  className?: string;
  readOnly?: boolean;
}

export const TerminalPanel = forwardRef<TerminalPanelHandle, TerminalPanelProps>(
  ({ onCommand, className, readOnly = false }, ref) => {
    const terminalRef = useRef<HTMLDivElement>(null);
    const xtermRef = useRef<Terminal | null>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);

    useImperativeHandle(ref, () => ({
      appendOutput: (text: string) => {
        const term = xtermRef.current;
        if (!term) return;
        const lines = text.split('\n');
        for (const line of lines) {
          term.write('\r\n');
          term.writeln(line);
        }
        term.write('\x1b[1;32m➜\x1b[0m \x1b[37m~\x1b[0m ');
      },
    }));

    useEffect(() => {
      if (!terminalRef.current) return;

      const term = new Terminal({
        // xterm 主题需要具体色值（不支持 CSS 变量），此处为终端专用配色（Slate 色系），
        // 与设计令牌体系解耦，属有意为之的硬编码。
        theme: {
          background: '#0F172A',
          foreground: '#F8FAFC',
          cursor: '#22C55E',
          cursorAccent: '#0F172A',
          selectionBackground: '#334155',
          black: '#0F172A',
          red: '#EF4444',
          green: '#22C55E',
          yellow: '#F59E0B',
          blue: '#3B82F6',
          magenta: '#A855F7',
          cyan: '#06B6D4',
          white: '#F8FAFC',
          brightBlack: '#64748B',
          brightRed: '#F87171',
          brightGreen: '#4ADE80',
          brightYellow: '#FBBF24',
          brightBlue: '#60A5FA',
          brightMagenta: '#C084FC',
          brightCyan: '#22D3EE',
          brightWhite: '#FFFFFF',
        },
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
        lineHeight: 1.4,
        letterSpacing: 0.5,
        cursorBlink: true,
        cursorStyle: 'bar',
        scrollback: 10000,
        tabStopWidth: 4,
      });

      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      term.open(terminalRef.current);
      fitAddon.fit();

      xtermRef.current = term;
      fitAddonRef.current = fitAddon;

      term.writeln('\x1b[1;32m┌────────────────────────────────────────┐\x1b[0m');
      term.writeln('\x1b[1;32m│\x1b[0m  \x1b[1;37mClimber Agent Sandbox\x1b[0m                   \x1b[1;32m│\x1b[0m');
      term.writeln('\x1b[1;32m│\x1b[0m  \x1b[90mType commands to interact with the agent\x1b[0m  \x1b[1;32m│\x1b[0m');
      term.writeln('\x1b[1;32m└────────────────────────────────────────┘\x1b[0m');
      term.writeln('');
      term.write('\x1b[1;32m➜\x1b[0m \x1b[37m~\x1b[0m ');

      if (!readOnly && onCommand) {
        term.onData((data) => {
          if (data === '\r') {
            term.write('\r\n');
            const line = (term as any)._lines?.map((l: any) => l.translateToString(0)).join('') || '';
            const match = line.match(/➜ .*~\s*(.*)$/);
            if (match) {
              onCommand(match[1].trim());
            }
          } else if (data === '\u007F') {
            term.write('\b \b');
          } else {
            term.write(data);
          }
        });
      }

      const handleResize = () => {
        fitAddon.fit();
      };
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        term.dispose();
        xtermRef.current = null;
        fitAddonRef.current = null;
      };
    }, [onCommand, readOnly]);

    return <div ref={terminalRef} className={cn('h-full w-full rounded-lg overflow-hidden', className)} />;
  }
);

TerminalPanel.displayName = 'TerminalPanel';

export default TerminalPanel;
