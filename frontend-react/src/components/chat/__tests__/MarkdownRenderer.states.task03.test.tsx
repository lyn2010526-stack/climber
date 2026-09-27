import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from '../MarkdownRenderer';

describe('MarkdownRenderer state and safety contract', () => {
  it('renders tables inside a horizontally scrollable region', () => {
    const { container } = render(<MarkdownRenderer content={'| Name | State |\n| --- | --- |\n| run | ready |'} />);
    expect(container.querySelector('.overflow-x-auto')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('keeps code controls available for a fenced block', () => {
    render(<MarkdownRenderer content={'```ts\nconst answer = 42;\n```'} />);
    expect(screen.getByTitle('复制代码')).toBeInTheDocument();
    expect(screen.getByTitle('行号')).toBeInTheDocument();
  });

  it('drops unsupported link schemes while preserving safe links', () => {
    render(<MarkdownRenderer content={'[safe](https://example.com) [unsafe](javascript:alert(1))'} />);
    expect(screen.getByRole('link', { name: 'safe' })).toHaveAttribute('href', 'https://example.com');
    expect(screen.queryByRole('link', { name: 'unsafe' })).not.toBeInTheDocument();
  });
});
