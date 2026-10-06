import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { DiffCell, parseDiffCell } from './DiffCell';

const diff = [
  'diff --git a/src/app.ts b/src/app.ts',
  '@@ -1,3 +1,3 @@',
  ' const a = 1;',
  '-const b = 2;',
  '+const b = 3;',
  ' const c = 4;',
].join('\n');

describe('parseDiffCell', () => {
  it('reads the path, counts and single-column line numbers', () => {
    const parsed = parseDiffCell(diff);
    expect(parsed.path).toBe('src/app.ts');
    expect(parsed.added).toBe(1);
    expect(parsed.removed).toBe(1);
    expect(parsed.lines.map((line) => line.sign)).toEqual([' ', '-', '+', ' ']);
    expect(parsed.lines[1]).toMatchObject({ oldNo: 2, newNo: null, text: 'const b = 2;' });
    expect(parsed.lines[2]).toMatchObject({ oldNo: null, newNo: 2, text: 'const b = 3;' });
  });

  it('falls back to the old path for a deleted file', () => {
    const parsed = parseDiffCell('diff --git a/gone.txt b/gone.txt\n--- a/gone.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-bye');
    expect(parsed.path).toBe('gone.txt');
    expect(parsed.removed).toBe(1);
  });
});

describe('DiffCell', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('zh-CN');
  });

  it('renders the codex header, `└` path line and one row per diff line', () => {
    render(<DiffCell diffText={diff} />);
    const cell = screen.getByTestId('anchored-diff-cell');
    expect(cell).toHaveAttribute('role', 'table');
    expect(cell).toHaveAttribute('aria-label', '代码差异');
    expect(cell).toHaveTextContent('已编辑');
    expect(cell).toHaveTextContent('src/app.ts');
    expect(cell).toHaveTextContent('+1');
    expect(cell).toHaveTextContent('-1');
    expect(cell).toHaveTextContent('└ src/app.ts');
    expect(screen.getAllByRole('row')).toHaveLength(4);
  });

  it('shows a placeholder path when the diff names no file', () => {
    render(<DiffCell diffText="@@ -1 +1 @@\n-a\n+b" />);
    expect(screen.getByTestId('anchored-diff-cell')).toHaveTextContent('未命名文件');
  });
});
