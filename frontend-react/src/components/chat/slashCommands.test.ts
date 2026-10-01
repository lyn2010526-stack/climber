import { describe, expect, it } from 'vitest';
import {
  FALLBACK_COMMANDS,
  completionsFor,
  extractCommandHead,
  findCommand,
  resolveCommand,
} from './slashCommands';

describe('extractCommandHead', () => {
  it('returns null for plain text', () => {
    expect(extractCommandHead('hello world')).toBeNull();
    expect(extractCommandHead('')).toBeNull();
  });

  it('returns the first token for slash input', () => {
    expect(extractCommandHead('/help')).toBe('help');
    expect(extractCommandHead('  /model openai:gpt-4o')).toBe('model');
    expect(extractCommandHead('/HELP')).toBe('help');
  });

  it('returns null for a bare slash', () => {
    expect(extractCommandHead('/')).toBeNull();
  });
});

describe('findCommand', () => {
  it('resolves aliases case-insensitively', () => {
    expect(findCommand(FALLBACK_COMMANDS, 'cancel')?.name).toBe('stop');
    expect(findCommand(FALLBACK_COMMANDS, 'STOP')?.name).toBe('stop');
    expect(findCommand(FALLBACK_COMMANDS, 'nope')).toBeUndefined();
    expect(findCommand(FALLBACK_COMMANDS, null)).toBeUndefined();
  });
});

describe('resolveCommand', () => {
  it('accepts exact command invocations', () => {
    const resolved = resolveCommand(FALLBACK_COMMANDS, '/clear');
    expect(resolved?.command.name).toBe('clear');
    expect(resolved?.rest).toBe('');
    expect(resolveCommand(FALLBACK_COMMANDS, '/help retry')?.rest).toBe('retry');
  });

  it('rejects non-command slash text (paths, fractions)', () => {
    expect(resolveCommand(FALLBACK_COMMANDS, '/etc/hosts is a file')).toBeNull();
    expect(resolveCommand(FALLBACK_COMMANDS, '/2.5 of budget')).toBeNull();
    expect(resolveCommand(FALLBACK_COMMANDS, '/')).toBeNull();
    expect(resolveCommand(FALLBACK_COMMANDS, 'plain question')).toBeNull();
  });
});

describe('completionsFor', () => {
  it('filters by prefix', () => {
    const names = completionsFor(FALLBACK_COMMANDS, 'st', false).map(c => c.name);
    expect(names).toEqual(['status', 'stop']);
  });

  it('includes /stop while streaming and excludes the rest', () => {
    const names = completionsFor(FALLBACK_COMMANDS, '', true).map(c => c.name);
    expect(names).toEqual(['stop']);
  });

  it('matches aliases while typing', () => {
    const names = completionsFor(FALLBACK_COMMANDS, 'can', true).map(c => c.name);
    expect(names).toEqual(['stop']);
  });
});
