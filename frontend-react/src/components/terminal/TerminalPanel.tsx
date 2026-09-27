import React, { useEffect, useRef, useState } from 'react';
import { Eraser, LoaderCircle, TerminalSquare } from 'lucide-react';
import { Terminal, type ITheme } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { cn } from '../../lib/utils';

interface TerminalPanelProps {
  onCommand?: (command: string) => void | string | string[] | Promise<void | string | string[]>;
  className?: string;
  readOnly?: boolean;
}

/**
 * Terminal palette expressed as design tokens.
 *
 * xterm runs every theme string through its own colour parser, which only
 * understands the hexadecimal and `rgb` / `rgba` notations. A CSS variable
 * reference fails to parse there, so the slot silently falls back to xterm's
 * default instead of painting the token. The values are therefore resolved
 * through `getComputedStyle` and re-read on every theme switch, and this file
 * holds no colour literal of its own.
 *
 * The terminal is a code surface, so it follows `--color-code-bg`, which stays
 * dark in both themes, and the glyph colours come from the syntax and semantic
 * tokens. `minimumContrastRatio` below covers the slots whose token value alone
 * sits under 4.5:1 on that surface: the three semantic roles, whose light-theme
 * values are pressed for a light page, plus the comment grey and the type
 * mauve. xterm lifts those in 10% steps, which is the job the hand picked
 * literals used to do, and it keeps the hue, so a quiet token such as the muted
 * grey behind "no such file" notices still reads.
 */
export const TERMINAL_THEME_TOKENS = {
  background: '--color-code-bg',
  foreground: '--color-syntax-operator',
  // The Codex accent. `--color-accent` is the brand token, but its light-theme
  // value is pressed for a light page, so the accent hue that lives on the code
  // surface is used instead; on the terminal background it holds 8:1 in both
  // themes and is the Codex accent in the default dark theme.
  cursor: '--color-syntax-function',
  cursorAccent: '--color-code-bg',
  selectionBackground: '--color-accent-subtle',
  black: '--color-code-bg',
  red: '--color-error',
  green: '--color-success',
  yellow: '--color-warning',
  blue: '--color-syntax-string',
  magenta: '--color-syntax-type',
  cyan: '--color-syntax-function',
  white: '--color-syntax-operator',
  brightBlack: '--color-syntax-comment',
  brightRed: '--color-error',
  brightGreen: '--color-success',
  brightYellow: '--color-warning',
  brightBlue: '--color-syntax-number',
  brightMagenta: '--color-syntax-type',
  brightCyan: '--color-syntax-function',
  brightWhite: '--color-syntax-operator',
} as const satisfies Partial<Record<keyof ITheme, string>>;

type ThemeSlot = keyof typeof TERMINAL_THEME_TOKENS;

const THEME_SLOTS = Object.keys(TERMINAL_THEME_TOKENS) as ThemeSlot[];

/**
 * Resolves the palette from the computed style of the terminal host, so a
 * scoped theme block wins over the document root. An undeclared token resolves
 * to an empty string; that slot is then left unset and xterm keeps its own
 * default, which is safer than handing the parser a value it cannot read.
 */
const readTerminalTheme = (source: Element): ITheme => {
  const computed = getComputedStyle(source);
  const theme: ITheme = {};
  for (const slot of THEME_SLOTS) {
    const value = computed.getPropertyValue(TERMINAL_THEME_TOKENS[slot]).trim();
    if (value) theme[slot] = value;
  }
  return theme;
};

export const TerminalPanel: React.FC<TerminalPanelProps> = ({ onCommand, className, readOnly = false }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    if (!terminalRef.current) return;
    const host = terminalRef.current;

    const term = new Terminal({
      theme: readTerminalTheme(host),
      // Terminal output is text, so every glyph is held to 4.5:1 against the
      // terminal background. The palette used to satisfy that with hand picked
      // literals; the option makes the token layer responsible for it instead.
      minimumContrastRatio: 4.5,
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
    term.open(host);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // `data-theme` on the document root is the only switch the token layer has,
    // so a theme change is an attribute change worth re-reading the palette for.
    const themeObserver = new MutationObserver(() => {
      term.options.theme = readTerminalTheme(host);
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });

    let disposed = false;
    setExecuting(false);
    term.writeln('\x1b[90mClimber Sandbox / Command API\x1b[0m');
    term.writeln(readOnly || !onCommand ? 'Read-only terminal.' : 'Enter a command. Use clear to clear the screen.');
    if (!readOnly && onCommand) term.write('\x1b[1;32m$\x1b[0m ');

    if (!readOnly && onCommand) {
      let commandBuffer = '';
      let isExecuting = false;
      const promptText = () => '\x1b[1;32m$\x1b[0m ';
      const writePrompt = () => term.write(promptText());

      term.onData((data) => {
        if (isExecuting) return;

        if (data === '\r') {
          const command = commandBuffer.trim();
          commandBuffer = '';
          term.write('\r\n');
          if (!command) {
            writePrompt();
            return;
          }

          isExecuting = true;
          setExecuting(true);
          Promise.resolve().then(() => onCommand(command)).then((out) => {
            if (disposed) return;
            const text = Array.isArray(out) ? out.join('\r\n') : String(out ?? '');
            if (text) term.write(text.endsWith('\n') ? `\r\n${text}` : `\r\n${text}\r\n`);
          }).catch((err) => {
            if (disposed) return;
            term.write(`\r\n\x1b[31m${String(err?.message ?? err)}\x1b[0m\r\n`);
          }).finally(() => {
            if (disposed) return;
            isExecuting = false;
            setExecuting(false);
            writePrompt();
          });
          return;
        }

        if (data === '\u007F') {
          if (commandBuffer.length > 0) {
            commandBuffer = commandBuffer.slice(0, -1);
            term.write('\b \b');
          }
          return;
        }

        if (data >= ' ' && data !== '\u007F') {
          commandBuffer += data;
          term.write(data);
        }
      });
    }

    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);
    const observer = new ResizeObserver(handleResize);
    observer.observe(host);

    return () => {
      disposed = true;
      themeObserver.disconnect();
      observer.disconnect();
      window.removeEventListener('resize', handleResize);
      term.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [onCommand, readOnly]);

  return (
    <section aria-label="沙箱终端" className={cn('flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-md border border-[var(--color-border-subtle)]', className)}>
      <div className="flex min-h-10 flex-wrap items-center gap-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 text-xs">
        <TerminalSquare size={14} aria-hidden="true" />
        <span className="font-medium">沙箱终端</span>
        <span role="status" className="flex items-center gap-1.5 text-[var(--color-text-muted)]">
          {executing && <LoaderCircle size={12} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />}
          {readOnly || !onCommand ? '只读' : executing ? '执行中' : '等待命令'}
        </span>
        <button type="button" onClick={() => { xtermRef.current?.clear(); xtermRef.current?.focus(); }}
          disabled={executing} className="ml-auto inline-flex min-h-9 items-center gap-1.5 rounded px-2 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] disabled:opacity-50">
          <Eraser size={14} aria-hidden="true" />清屏
        </button>
      </div>
      <div className="min-h-0 flex-1 bg-[var(--color-code-bg)] p-2">
        <div ref={terminalRef} className="h-full w-full overflow-hidden" />
      </div>
    </section>
  );
};

export default TerminalPanel;
