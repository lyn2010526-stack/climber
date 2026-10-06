import { describe, expect, it } from 'vitest';
import type { Message, ToolCall } from '../../useChat';
import { entriesForToolCall, isFileMutationTool, isWebsiteTool, mergeDeliverables, selectTurnDeliverables } from './deliverables';

function call(overrides: Partial<ToolCall> & Pick<ToolCall, 'name' | 'arguments'>): ToolCall {
  return { id: 'call-1', status: 'success', result: 'done', error: undefined, ...overrides };
}

describe('isFileMutationTool / isWebsiteTool', () => {
  it('recognizes file tools by token root', () => {
    expect(isFileMutationTool('write_file')).toBe(true);
    expect(isFileMutationTool('edit')).toBe(true);
    expect(isFileMutationTool('apply_patch')).toBe(true);
    expect(isFileMutationTool('read_file')).toBe(false);
  });

  it('recognizes website tools by token root', () => {
    expect(isWebsiteTool('deploy_website')).toBe(true);
    expect(isWebsiteTool('preview')).toBe(true);
    expect(isWebsiteTool('write_file')).toBe(false);
  });
});

describe('entriesForToolCall', () => {
  it('derives added/removed from new_string and old_string', () => {
    const entries = entriesForToolCall(call({
      name: 'edit',
      arguments: { file_path: 'src/a.ts', old_string: 'a\nb', new_string: 'a\nb\nc' },
    }));
    expect(entries).toEqual([{ path: 'src/a.ts', added: 3, removed: 2, kind: 'file' }]);
  });

  it('falls back to diff counts in the result when only a path is given', () => {
    const entries = entriesForToolCall(call({
      name: 'write',
      arguments: { path: 'README.md' },
      result: '--- README\n+++ README\n+new line\n-removed line\nunchanged',
    }));
    expect(entries).toEqual([{ path: 'README.md', added: 1, removed: 1, kind: 'file' }]);
  });

  it('counts content with a trailing newline without an extra line', () => {
    const entries = entriesForToolCall(call({
      name: 'write_file',
      arguments: { file_path: 'x.txt', content: 'a\n' },
    }));
    expect(entries[0].added).toBe(1);
  });

  it('emits nothing for a failed or unidentifiable call', () => {
    expect(entriesForToolCall(call({ name: 'edit', arguments: { file_path: 'a' }, error: { message: 'boom' } }))).toEqual([]);
    expect(entriesForToolCall(call({ name: 'read_file', arguments: { path: 'a' } }))).toEqual([]);
  });

  it('picks the website url from args', () => {
    const entries = entriesForToolCall(call({
      name: 'deploy',
      arguments: { url: 'https://example.com/app' },
    }));
    expect(entries).toEqual([{ path: 'https://example.com/app', added: 0, removed: 0, kind: 'website' }]);
  });

  it('extracts website urls from the result text', () => {
    const entries = entriesForToolCall(call({
      name: 'preview',
      arguments: {},
      result: 'Preview: https://example.com/preview, https://example.com/preview. and nothing else',
    }));
    expect(entries.map(entry => entry.path)).toEqual(['https://example.com/preview']);
  });
});

describe('mergeDeliverables', () => {
  it('merges repeated writes to the same path and keeps unique websites', () => {
    const merged = mergeDeliverables([
      { path: 'a.ts', added: 2, removed: 1, kind: 'file' },
      { path: 'a.ts', added: 1, removed: 0, kind: 'file' },
      { path: 'b.ts', added: 3, removed: 2, kind: 'file' },
    ]);
    expect(merged).toHaveLength(2);
    expect(merged[0]).toEqual({ path: 'a.ts', added: 3, removed: 1, kind: 'file' });
  });
});

describe('selectTurnDeliverables', () => {
  it('returns null when no assistant turn produced deliverables', () => {
    const user: Message = { id: 'u', role: 'user', content: 'hi' };
    const assistant: Message = { id: 'a', role: 'assistant', content: 'ok' };
    expect(selectTurnDeliverables([user, assistant])).toBeNull();
  });

  it('picks the most recent assistant turn that produced deliverables', () => {
    const older: Message = {
      id: 'a1', role: 'assistant', content: 'first',
      toolCalls: [call({ name: 'write_file', arguments: { file_path: 'old.ts', content: 'x' } })],
    };
    const latest: Message = {
      id: 'a2', role: 'assistant', content: 'second',
      toolCalls: [call({ name: 'write_file', arguments: { file_path: 'new.ts', content: 'y' } })],
    };
    const result = selectTurnDeliverables([older, latest]);
    expect(result).toEqual([{ path: 'new.ts', added: 1, removed: 0, kind: 'file' }]);
  });

  it('skips assistant turns that only read or chat', () => {
    const user: Message = { id: 'u', role: 'user', content: 'hi' };
    const readOnly: Message = {
      id: 'a1', role: 'assistant', content: 'looking',
      toolCalls: [call({ name: 'read_file', arguments: { path: 'a.ts' } })],
    };
    const edited: Message = {
      id: 'a2', role: 'assistant', content: 'fixed',
      toolCalls: [call({ name: 'edit', arguments: { file_path: 'a.ts', new_string: 'z', old_string: 'y' } })],
    };
    const result = selectTurnDeliverables([user, readOnly, edited]);
    expect(result).toEqual([{ path: 'a.ts', added: 1, removed: 1, kind: 'file' }]);
  });
});