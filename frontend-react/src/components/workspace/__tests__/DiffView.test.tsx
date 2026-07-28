import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DiffView } from '../DiffView';

const sampleDiffs = [
  {
    filename: 'src/app.tsx',
    status: 'modified' as const,
    diff: [
      { type: 'context' as const, content: 'import React from "react";', oldLine: 1, newLine: 1 },
      { type: 'added' as const, content: 'import { z } from "zod";', newLine: 2 },
      { type: 'removed' as const, content: 'const unused = true;', oldLine: 5 },
    ],
  },
];

describe('DiffView', () => {
  it('renders empty state when no diffs', () => {
    render(<DiffView diffs={[]} />);
    expect(screen.getByText('No changes to display')).toBeDefined();
  });

  it('renders file header with stats', () => {
    render(<DiffView diffs={sampleDiffs} />);
    expect(screen.getByText('src/app.tsx')).toBeDefined();
    expect(screen.getByText('modified')).toBeDefined();
  });

  it('toggles file expansion on click', () => {
    render(<DiffView diffs={sampleDiffs} />);
    const fileButton = screen.getByText('src/app.tsx').closest('button');
    fireEvent.click(fileButton!);
    expect(screen.getByText('import React from "react";')).toBeDefined();
  });

  it('shows added lines in green', () => {
    render(<DiffView diffs={sampleDiffs} />);
    const fileButton = screen.getByText('src/app.tsx').closest('button');
    fireEvent.click(fileButton!);
    expect(screen.getByText('import { z } from "zod";')).toBeDefined();
  });

  it('displays addition and removal counts', () => {
    render(<DiffView diffs={sampleDiffs} />);
    expect(screen.getByText('+1')).toBeDefined();
    expect(screen.getByText('-1')).toBeDefined();
  });
});
