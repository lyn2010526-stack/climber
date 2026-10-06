import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { WorkbenchIcon, type WorkbenchIconName } from '../WorkbenchIcon';

describe('original workbench semantic glyphs', () => {
  it('draws distinct local SVG paths with an accessible decorative contract', () => {
    const names: WorkbenchIconName[] = ['navigation', 'conversation', 'tool', 'task', 'knowledge', 'skill', 'settings', 'preview', 'agent', 'tree', 'meter'];
    const { container } = render(<>{names.map(name => <WorkbenchIcon key={name} name={name} />)}</>);
    const glyphs = [...container.querySelectorAll('svg')];
    expect(glyphs).toHaveLength(names.length);
    expect(new Set(glyphs.map(glyph => glyph.querySelector('path')?.getAttribute('d'))).size).toBe(names.length);
    glyphs.forEach((glyph, index) => {
      expect(glyph).toHaveAttribute('data-workbench-icon', names[index]);
      expect(glyph).toHaveAttribute('aria-hidden', 'true');
      expect(glyph).toHaveAttribute('focusable', 'false');
      expect(glyph).toHaveAttribute('viewBox', '0 0 20 20');
      expect(glyph).toHaveAttribute('stroke', 'currentColor');
    });
  });
});
