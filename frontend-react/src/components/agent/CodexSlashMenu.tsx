import { useMemo } from 'react';
import { cn } from '../../lib/utils';

export interface CodexSlashCommand {
  command: string;
  description: string;
}

export interface CodexSlashMenuProps {
  commands: CodexSlashCommand[];
  query?: string;
  activeIndex?: number;
  maxRows?: number;
  onSelect?: (command: CodexSlashCommand, index: number) => void;
  onHover?: (index: number) => void;
  visible?: boolean;
}

const DEFAULT_MAX_ROWS = 8;
const CONFIRM_HINT = 'Press enter to confirm or esc to go back';

interface Segment {
  text: string;
  match: boolean;
}

function segments(text: string, query: string): Segment[] {
  if (!query) return [{ text, match: false }];
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const result: Segment[] = [];
  let cursor = 0;
  while (cursor <= text.length) {
    const found = lowerText.indexOf(lowerQuery, cursor);
    if (found === -1) {
      result.push({ text: text.slice(cursor), match: false });
      break;
    }
    if (found > cursor) result.push({ text: text.slice(cursor, found), match: false });
    result.push({ text: text.slice(found, found + query.length), match: true });
    cursor = found + query.length;
  }
  return result.filter((segment) => segment.text.length > 0);
}

export function CodexSlashMenu({
  commands,
  query = '',
  activeIndex = 0,
  maxRows = DEFAULT_MAX_ROWS,
  onSelect,
  onHover,
  visible = true,
}: CodexSlashMenuProps) {
  const capped = useMemo(() => commands.slice(0, maxRows), [commands, maxRows]);
  const active = capped.length === 0 ? 0 : Math.min(Math.max(activeIndex, 0), capped.length - 1);

  if (!visible || capped.length === 0) return null;

  return (
    <div
      role="listbox"
      aria-label="slash-commands"
      data-testid="codex-slash-menu"
      className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-md)]"
    >
      <ul className="py-[var(--space-1)]">
        {capped.map((item, index) => {
          const isActive = index === active;
          return (
            <li key={item.command}>
              <button
                type="button"
                role="option"
                aria-selected={isActive}
                onMouseEnter={() => onHover?.(index)}
                onMouseDown={(event) => {
                  event.preventDefault();
                  onSelect?.(item, index);
                }}
                className={cn(
                  'flex w-full items-baseline gap-2 px-[var(--space-2)] py-[var(--space-1)] text-start font-mono text-[length:var(--text-xs)] transition-colors focus-visible:outline-none',
                  isActive
                    ? 'bg-[var(--color-accent-foreground)] font-bold text-[var(--color-bg-surface-1)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]',
                )}
              >
                {segments(`/${item.command} - ${item.description}`, query).map((segment, segmentIndex) => (
                  <span
                    key={segmentIndex}
                    className={segment.match ? cn('underline', isActive ? 'text-[var(--color-bg-surface-1)]' : 'text-[var(--color-text-primary)]') : undefined}
                  >
                    {segment.text}
                  </span>
                ))}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-[var(--color-border-subtle)] px-[var(--space-2)] py-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {CONFIRM_HINT}
      </p>
    </div>
  );
}

export default CodexSlashMenu;
