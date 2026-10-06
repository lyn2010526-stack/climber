import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from '../MarkdownRenderer';

const LONG_REPLY = [
  '## Overview',
  '',
  'Some body text.',
  '',
  '### Details',
  '',
  'More text.',
  '',
  '#### Caveats',
  '',
  'Last section.',
].join('\n');

describe('MarkdownRenderer table of contents', () => {
  it('hides the toc for short replies with fewer than three headings', () => {
    render(<MarkdownRenderer content={'## One\n\ntext\n\n## Two\n\ntext'} />);
    expect(screen.queryByRole('navigation')).toBeNull();
  });

  it('shows the toc once the heading count reaches the threshold', () => {
    render(<MarkdownRenderer content={LONG_REPLY} />);
    const nav = screen.getByRole('navigation');
    expect(nav).toBeInTheDocument();
  });

  it('lists every h2-h4 heading in document order', () => {
    render(<MarkdownRenderer content={LONG_REPLY} />);
    const links = screen.getAllByRole('link');
    expect(links.map(a => a.textContent)).toEqual(['Overview', 'Details', 'Caveats']);
  });

  it('gives each toc link a target that exists in the rendered headings', () => {
    const { container } = render(<MarkdownRenderer content={LONG_REPLY} />);
    const hrefs = screen.getAllByRole('link').map(a => a.getAttribute('href'));
    expect(hrefs).toHaveLength(3);
    for (const href of hrefs) {
      expect(href).toMatch(/^#heading-/);
      const id = href!.slice(1);
      expect(container.querySelector(`#${CSS.escape(id)}`)).not.toBeNull();
    }
  });

  it('produces unique ids for repeated heading text', () => {
    const { container } = render(
      <MarkdownRenderer content={'## Setup\n\na\n\n## Setup\n\nb\n\n## Setup\n\nc'} />,
    );
    const ids = Array.from(container.querySelectorAll('h2')).map(h => h.id);
    expect(ids).toHaveLength(3);
    expect(new Set(ids).size).toBe(3);
  });

  it('ignores hash lines inside fenced code blocks', () => {
    render(<MarkdownRenderer content={'## A\n\ntext\n\n## B\n\ntext\n\n## C\n\n```sh\n# not a heading\n```\n'} />);
    const links = screen.getAllByRole('link').map(a => a.textContent);
    expect(links).toEqual(['A', 'B', 'C']);
  });

  it('renders the toc when showToc is forced on a short reply', () => {
    render(<MarkdownRenderer content={'## Only\n\ntext'} showToc />);
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('indents nested headings by level', () => {
    const { container } = render(<MarkdownRenderer content={LONG_REPLY} />);
    const items = container.querySelectorAll('nav ol > li');
    expect(items[0]!.getAttribute('style')).toContain('padding-left: 0px');
    expect(items[1]!.getAttribute('style')).toContain('padding-left: 12px');
    expect(items[2]!.getAttribute('style')).toContain('padding-left: 24px');
  });

  it('keeps toc anchors aligned when headings carry inline markdown', () => {
    const content = [
      '## **Bold** title',
      '',
      'text',
      '',
      '### `code` heading',
      '',
      'text',
      '',
      '#### [Linked](https://example.com) title',
      '',
      'text',
    ].join('\n');
    const { container } = render(<MarkdownRenderer content={content} />);
    const links = screen.getAllByRole('link').filter(a => a.getAttribute('href')?.startsWith('#heading-'));
    expect(links.map(a => a.textContent)).toEqual(['Bold title', 'code heading', 'Linked title']);
    for (const link of links) {
      const id = link.getAttribute('href')!.slice(1);
      expect(container.querySelector(`#${CSS.escape(id)}`)).not.toBeNull();
    }
  });
});
