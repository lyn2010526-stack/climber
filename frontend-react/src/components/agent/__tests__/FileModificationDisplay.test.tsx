import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FileModificationDisplay, type FileChange } from '../FileModificationDisplay';

const mockChanges: FileChange[] = [
  {
    path: '/test/file1.ts',
    type: 'created',
    additions: 10,
    preview: 'New file content',
  },
  {
    path: '/test/file2.ts',
    type: 'modified',
    additions: 5,
    deletions: 2,
    diff: '@@ -1,3 +1,3 @@',
  },
  {
    path: '/test/file3.ts',
    type: 'deleted',
    deletions: 15,
  },
];

describe('FileModificationDisplay', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <FileModificationDisplay changes={mockChanges} />
    );
    expect(container).toBeDefined();
  });

  it('renders file names', () => {
    render(<FileModificationDisplay changes={mockChanges} />);
    expect(screen.getByText('file1.ts')).toBeDefined();
    expect(screen.getByText('file2.ts')).toBeDefined();
    expect(screen.getByText('file3.ts')).toBeDefined();
  });

  it('renders change type labels', () => {
    render(<FileModificationDisplay changes={mockChanges} />);
    expect(screen.getByText('新增')).toBeDefined();
    expect(screen.getByText('修改')).toBeDefined();
    expect(screen.getByText('删除')).toBeDefined();
  });

  it('renders additions/deletions count', () => {
    render(<FileModificationDisplay changes={mockChanges} />);
    expect(screen.getByText('+10')).toBeDefined();
    expect(screen.getByText('-2')).toBeDefined();
  });

  it('renders directory paths', () => {
    render(<FileModificationDisplay changes={mockChanges} />);
    expect(screen.getAllByText('/test/').length).toBeGreaterThan(0);
  });
});
