import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from '../MarkdownRenderer';

describe('MarkdownRenderer', () => {
  it('renders plain text', () => {
    render(<MarkdownRenderer content="Hello world" />);
    expect(screen.getByText('Hello world')).toBeDefined();
  });

  it('renders bold text', () => {
    render(<MarkdownRenderer content="**bold**" />);
    expect(screen.getByText('bold')).toBeDefined();
  });

  it('renders code blocks', () => {
    const { container } = render(<MarkdownRenderer content="```js\nconst x = 1;\n```" />);
    const codeBlocks = container.querySelectorAll('code');
    expect(codeBlocks.length).toBeGreaterThan(0);
  });

  it('renders links', () => {
    render(<MarkdownRenderer content="[link](https://example.com)" />);
    expect(screen.getByText('link')).toBeDefined();
  });
});
