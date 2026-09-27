import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Modal, MODAL_DEPTHS } from '../Modal';
import { Dropdown, DropdownItem, DropdownSubMenu, DropdownHeader } from '../Dropdown';
import { EmptyState } from '../EmptyState';
import { ThemeToggle } from '../ThemeToggle';
import { ThemeProvider } from '../../../hooks/useTheme';
import { icons, iconSizes } from '../../../lib/icons';
import { TONE_GLYPH, TONE_TEXT } from '../StatusIcon';

afterEach(cleanup);

const uiDir = resolve(process.cwd(), 'src/components/ui');
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');
const sourceOf = (file: string) => readFileSync(resolve(uiDir, file), 'utf-8');

const OVERLAY_FILES = ['Modal.tsx', 'Dropdown.tsx', 'EmptyState.tsx', 'ThemeToggle.tsx'] as const;

describe('modal depth ladder', () => {
  const openModal = (depth?: 'default' | 'elevated' | 'overlay' | 'backdrop') =>
    render(<Modal open title="Settings" onClose={vi.fn()} depth={depth}>Body</Modal>);

  it('gives every rung a scrim, a panel fill, an edge and a lift', () => {
    expect(Object.keys(MODAL_DEPTHS)).toEqual(['default', 'elevated', 'overlay', 'backdrop']);
    for (const [depth, spec] of Object.entries(MODAL_DEPTHS)) {
      // The scrim is the page colour at partial alpha, so it dims toward the
      // theme's own base instead of introducing a second backdrop colour.
      expect(spec.scrim, depth).toMatch(/^bg-\[var\(--color-bg-page\)\]\/\d{2}$/);
      expect(spec.panel, depth).toMatch(/^bg-\[var\(--color-bg-surface-[12]\)\]$/);
      expect(spec.edge, depth).toMatch(/^border-\[var\(--color-border-(?:default|strong)\)\]$/);
      // Level only. A rung never tints or blurs its own panel.
      expect(spec.shadow, depth).toMatch(/^shadow-\[var\(--shadow-(?:lg|xl)\)\]$/);
    }
  });

  it('paints the panel and the scrim from the ladder the caller asked for', () => {
    const { rerender } = openModal();
    const panel = () => screen.getByRole('dialog');
    const scrim = () => document.querySelector('[data-modal-overlay]')!;
    expect(panel()).toHaveClass('bg-[var(--color-bg-surface-1)]', 'border-[var(--color-border-default)]', 'shadow-[var(--shadow-lg)]');
    expect(panel()).toHaveAttribute('data-depth', 'default');
    expect(scrim()).toHaveClass('bg-[var(--color-bg-page)]/80');
    // A second scrim from a previous render must not linger.
    expect(document.querySelectorAll('[data-modal-overlay]')).toHaveLength(1);

    rerender(<Modal open title="Settings" onClose={vi.fn()} depth="elevated">Body</Modal>);
    expect(panel()).toHaveClass('bg-[var(--color-bg-surface-2)]', 'border-[var(--color-border-strong)]', 'shadow-[var(--shadow-xl)]');
    expect(panel()).toHaveAttribute('data-depth', 'elevated');

    rerender(<Modal open title="Settings" onClose={vi.fn()} depth="backdrop">Body</Modal>);
    expect(panel()).toHaveClass('bg-[var(--color-bg-surface-1)]', 'shadow-[var(--shadow-xl)]');
    expect(scrim()).toHaveClass('bg-[var(--color-bg-page)]/92');
  });

  it('orders the scrim so the overlay rung lets its host stay readable', () => {
    const alpha = (depth: 'default' | 'elevated' | 'overlay' | 'backdrop') =>
      Number(MODAL_DEPTHS[depth].scrim.replace(/^bg-\[var\(--color-bg-page\)\]\//, ''));
    expect(alpha('overlay')).toBeLessThan(alpha('default'));
    expect(alpha('default')).toBeLessThan(alpha('backdrop'));
    // The lift never inverts the scrim order: a deeper stack still reads deeper.
    expect(alpha('elevated')).toBe(alpha('default'));
  });

  it('dims the scrim with alpha alone, leaving the control layer unfrosted', () => {
    const { container } = openModal();
    const scrim = document.querySelector('[data-modal-overlay]')!;
    const alpha = Number(
      MODAL_DEPTHS.default.scrim.replace(/^bg-\[var\(--color-bg-page\)\]\//, ''),
    );
    // With no glass filter on the scrim, opacity is the only thing taking the
    // host out of focus, so the default rung has to be dark enough to do it.
    expect(alpha).toBeGreaterThanOrEqual(75);
    expect(scrim.className).not.toMatch(/backdrop-blur|backdrop-filter|blur-/);
    // The dim belongs to the scrim alone: the panel and the shell around it
    // never grow a filter of their own.
    expect(screen.getByRole('dialog').className).not.toMatch(/backdrop-blur|backdrop-filter|blur-/);
    expect(container.innerHTML).not.toMatch(/gradient|backdrop/);
  });

  it('keeps focus trapped, Escape wired and the scroll lock released', async () => {
    const onClose = vi.fn();
    const { rerender } = render(<button>Open</button>);
    // The opener is where focus has to come back to once the dialog closes.
    (screen.getByRole('button', { name: 'Open' }) as HTMLElement).focus();
    rerender(
      <>
        <button>Open</button>
        <Modal open title="Settings" onClose={onClose} showClose={false}>
          <button disabled>Unavailable</button>
          <button>Save</button>
          <button>Cancel</button>
        </Modal>
      </>,
    );
    const dialog = screen.getByRole('dialog');
    await waitFor(() => expect(dialog).toHaveFocus());
    // Shift+Tab from the panel itself wraps to the last stop rather than
    // escaping to the opener behind the scrim.
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
    // A disabled row is not a tab stop, so Tab walks the two live buttons and
    // then wraps back to the first instead of leaving the dialog.
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(screen.getByRole('button', { name: 'Save' })).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(screen.getByRole('button', { name: 'Save' })).toHaveFocus();
    expect(document.body.style.overflow).toBe('hidden');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();

    rerender(<button>Open</button>);
    expect(screen.getByRole('button', { name: 'Open' })).toHaveFocus();
    expect(document.body.style.overflow).toBe('');
  });

  it('closes from the close button, which draws the shared close glyph', () => {
    const onClose = vi.fn();
    render(<Modal open title="Settings" onClose={onClose}>Body</Modal>);
    const close = screen.getByRole('button', { name: /关闭|close/i });
    expect(close.querySelector('svg')).toHaveAttribute('width', String(iconSizes.md));
    // The affordance sits on the muted rung at rest and takes the shared ring,
    // so it never draws its own outline over the panel.
    expect(close).toHaveClass('text-[var(--color-text-muted)]', 'focus-visible:outline-none', 'focus-visible:shadow-[var(--focus-ring)]');
    fireEvent.click(close);
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe('dropdown menu surface', () => {
  const openMenu = (children: React.ReactNode) =>
    render(<Dropdown trigger="Actions">{children}</Dropdown>);

  it('floats the panel on surface-1 behind a border-default edge and one shadow', () => {
    openMenu(<DropdownItem>Export</DropdownItem>);
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    const menu = screen.getByRole('menu');
    expect(menu).toHaveClass('bg-[var(--color-bg-surface-1)]');
    expect(menu).toHaveClass('border-[var(--color-border-default)]');
    // `--shadow-lg` is the floating-panel rung; a menu is not a dialog.
    expect(menu).toHaveClass('shadow-[var(--shadow-lg)]');
    expect(menu.className).not.toMatch(/shadow-(?:sm|md|xl|2xl)\b/);
    expect(menu.className).not.toMatch(/gradient|backdrop-blur/);
  });

  it('gives a submenu the same panel recipe as the menu that owns it', () => {
    render(
      <Dropdown trigger="Actions">
        <DropdownSubMenu trigger="More">
          <DropdownItem>Export</DropdownItem>
        </DropdownSubMenu>
      </Dropdown>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    fireEvent.click(screen.getByRole('menuitem', { name: 'More' }));
    const [menu, submenu] = screen.getAllByRole('menu');
    // The nested panel is the same surface recipe, only re-anchored, so a
    // submenu cannot quietly become a second menu look.
    for (const recipe of [
      'bg-[var(--color-bg-surface-1)]',
      'border-[var(--color-border-default)]',
      'shadow-[var(--shadow-lg)]',
      'rounded-[var(--radius-lg)]',
    ]) {
      expect(menu, recipe).toHaveClass(recipe);
      expect(submenu, recipe).toHaveClass(recipe);
    }
  });

  it('steps a row from surface-2 on hover and spends the accent on selection', () => {
    const { container } = openMenu(
      <>
        <DropdownItem>Export</DropdownItem>
        <DropdownItem selected>Compact</DropdownItem>
        <DropdownItem danger>Delete</DropdownItem>
      </>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    const [plain, selected, danger] = screen.getAllByRole('menuitem');

    // At rest a row is secondary text with no fill; hover only adds surface-2.
    expect(plain).toHaveClass('text-[var(--color-text-secondary)]');
    expect(plain).toHaveClass('enabled:hover:bg-[var(--color-bg-surface-2)]');
    expect(plain).not.toHaveClass('bg-[var(--color-accent-subtle)]');

    // Selection is the one accent the menu spends, and it is announced.
    expect(selected).toHaveClass('bg-[var(--color-accent-subtle)]', 'text-[var(--color-accent-foreground)]');
    expect(selected).toHaveAttribute('aria-current', 'true');
    expect(selected).toHaveAttribute('data-selected', 'true');
    // Hover must not repaint a selected row, or the fill stops meaning "here".
    expect(selected.className).not.toMatch(/hover:bg-\[var\(--color-bg-surface-2\)\]/);
    expect(container.querySelectorAll('[data-selected]')).toHaveLength(1);

    // A destructive row keeps the error hue, which is a status, not a selection.
    expect(danger).toHaveClass('text-[var(--color-error)]', 'enabled:hover:bg-[var(--color-error-subtle)]');
    expect(danger).not.toHaveClass('bg-[var(--color-accent-subtle)]');
    // Exactly one row is the accent, so a menu of many still has one focal row.
    expect(container.querySelectorAll('[data-selected]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-selected][aria-current="true"]')).toHaveLength(1);
  });

  it('resolves disabled before selection, so a dead row never reads as current', () => {
    openMenu(
      <>
        <DropdownItem selected disabled>Compact</DropdownItem>
        <DropdownItem selected>Full</DropdownItem>
      </>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    const [dead, live] = screen.getAllByRole('menuitem');
    expect(dead).toHaveClass('text-[var(--color-text-disabled)]', 'cursor-not-allowed');
    expect(dead.className).not.toMatch(/color-accent/);
    expect(dead).toBeDisabled();
    // A blanket fade would wash the label out and leave the row looking live.
    expect(dead.className).not.toMatch(/opacity-/);
    expect(live).toHaveClass('bg-[var(--color-accent-subtle)]');
  });

  it('names a group on the muted rung with no interactive state of its own', () => {
    const { container } = openMenu(<DropdownHeader>Export</DropdownHeader>);
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    const heading = screen.getByText('Export');
    expect(heading).toHaveClass('text-[var(--color-text-muted)]');
    // A heading is a label, so it must not become a tab stop or a hover target.
    expect(heading).not.toHaveAttribute('tabindex');
    expect(heading.className).not.toMatch(/hover:|focus:/);
    expect(container.querySelectorAll('[role="menuitem"]')).toHaveLength(0);
  });

  it('points a submenu at the shared chevron, sized off the icon ladder', () => {
    const { container } = openMenu(
      <DropdownSubMenu trigger="More">
        <DropdownItem>Export</DropdownItem>
      </DropdownSubMenu>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    const row = screen.getByRole('menuitem', { name: 'More' });
    // The chevron is decorative, so it is matched by its own box rather than
    // through the accessibility tree, which hides it on purpose.
    const chevron = row.querySelector('svg')!;
    expect(chevron).toHaveAttribute('width', String(iconSizes.xs));
    expect(chevron).toHaveClass('text-[var(--color-text-muted)]');
    expect(container.querySelector('svg')).toBe(chevron);
  });

  it('keeps roving focus, wrapping and Escape wired across the rows', async () => {
    const onOpenChange = vi.fn();
    render(
      <Dropdown trigger={<button type="button" aria-label="Open actions">Actions</button>} onOpenChange={onOpenChange}>
        <DropdownItem>Export</DropdownItem>
        <DropdownItem disabled>Delete</DropdownItem>
        <DropdownItem>Rename</DropdownItem>
      </Dropdown>
    );
    const trigger = screen.getByRole('button', { name: 'Open actions' });
    trigger.focus();
    fireEvent.keyDown(trigger, { key: 'Enter' });
    const menu = screen.getByRole('menu');
    const items = screen.getAllByRole('menuitem');
    // Focus lands on the first enabled row when the menu opens.
    await waitFor(() => expect(items[0]).toHaveFocus());
    // A disabled row is stepped over in both directions.
    fireEvent.keyDown(menu, { key: 'ArrowDown' });
    expect(items[2]).toHaveFocus();
    fireEvent.keyDown(menu, { key: 'ArrowDown' });
    expect(items[0]).toHaveFocus();
    fireEvent.keyDown(menu, { key: 'End' });
    expect(items[2]).toHaveFocus();
    fireEvent.keyDown(menu, { key: 'Home' });
    expect(items[0]).toHaveFocus();
    // Every row takes the shared ring, so focus is visible on all of them.
    for (const item of items) {
      expect(item).toHaveClass('focus-visible:outline-none', 'focus-visible:shadow-[var(--focus-ring)]');
    }
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).toBeNull();
    expect(trigger).toHaveFocus();
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
  });
});

describe('empty state icon semantics', () => {
  it('routes every named state through StatusIcon instead of drawing a glyph', () => {
    const cases = [
      ['alert', 'error'],
      ['warning', 'warning'],
      ['unreported', 'unknown'],
      ['queued', 'queued'],
      ['approval', 'approval'],
    ] as const;
    for (const [name, tone] of cases) {
      const { container, unmount } = render(<EmptyState title="Nothing here" icon={name} />);
      // The tone's own glyph, its own rung: one vocabulary for every control.
      const Glyph = TONE_GLYPH[tone];
      expect(Glyph, name).toBeTruthy();
      expect(container.querySelector('svg'), name).toHaveClass(TONE_TEXT[tone]);
      expect(container.querySelector('svg'), name).toHaveAttribute('width', String(iconSizes.lg));
      expect(container.querySelector('svg'), name).toHaveAttribute('aria-hidden', 'true');
      unmount();
    }
  });

  it('draws the two agent-workbench states that are not outcomes', () => {
    // A queued run and an approval-blocked call are the states a waiting
    // panel shows, and they resolve to the two tones added for them.
    expect(TONE_GLYPH.queued).toBe(icons.queued);
    expect(TONE_GLYPH.approval).toBe(icons.approval);
    expect(TONE_TEXT.queued).toBe('text-[var(--color-text-disabled)]');
    expect(TONE_TEXT.approval).toBe('text-[var(--color-accent)]');

    const queued = render(<EmptyState title="Queued" icon="queued" />);
    expect(queued.container.querySelector('svg')).toHaveClass('text-[var(--color-text-disabled)]');
    const approval = render(<EmptyState title="Approval" icon="approval" />);
    // Waiting on a person is the one state the accent marks.
    expect(approval.container.querySelector('svg')).toHaveClass('text-[var(--color-accent)]');
  });

  it('keeps missing-thing artwork on the muted rung, clear of every state hue', () => {
    for (const [name, Glyph] of Object.entries({ inbox: icons.emptyInbox, search: icons.emptySearch, file: icons.emptyFile })) {
      const { container, unmount } = render(<EmptyState title="Nothing here" icon={name} />);
      const svg = container.querySelector('svg');
      expect(svg, name).toHaveClass('text-[var(--color-text-muted)]');
      expect(svg!.getAttribute('class'), name).not.toMatch(/--(?:color-error|color-success|color-warning|color-info|color-accent)/);
      expect(Glyph, name).toBeTruthy();
      expect(svg, name).toHaveAttribute('width', String(iconSizes.lg));
      unmount();
    }
  });

  it('steps the title and description down one rung each and keeps the action last', () => {
    render(
      <EmptyState
        title="No runs in this session"
        description="The workspace has no run records yet. Start a run from the sidebar."
        action={<button>New run</button>}
      />
    );
    expect(screen.getByRole('heading', { name: 'No runs in this session' })).toHaveClass('text-[var(--color-text-primary)]');
    const description = screen.getByText(/no run records yet/);
    expect(description).toHaveClass('text-[var(--color-text-muted)]');
    expect(description.className).not.toMatch(/color-accent|color-error|color-success/);
    expect(screen.getByRole('button', { name: 'New run' })).toBeInTheDocument();
  });

  it('takes caller artwork and a caller node verbatim', () => {
    const { container, rerender } = render(<EmptyState title="No files" icon="file" />);
    expect(container.querySelector('svg')).toHaveAttribute('width', String(iconSizes.lg));
    rerender(<EmptyState title="No files" illustration={<span>Artwork</span>} icon="file" />);
    // Artwork wins over the built-in glyph, so a caller can replace it.
    expect(screen.getByText('Artwork')).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeNull();
    rerender(<EmptyState title="No files" icon={<svg data-testid="custom" />} />);
    expect(screen.getByTestId('custom')).toBeInTheDocument();
  });
});

describe('theme toggle states', () => {
  const renderToggle = () =>
    render(
      <ThemeProvider defaultTheme="dark">
        <ThemeToggle />
      </ThemeProvider>
    );

  it('takes both theme glyphs from the shared icon table at one ladder rung', async () => {
    const { container } = renderToggle();
    // Dark shows the moon it is currently in. The glyph carries its identity
    // in the lucide class, which is what the shared icon table hands over.
    await waitFor(() => expect(container.querySelector('svg')).toHaveAttribute('width', String(iconSizes.md)));
    const toggle = screen.getByRole('button');
    expect(toggle).toHaveAttribute('data-state', 'dark');
    expect(container.querySelector('svg')).toHaveClass('lucide-moon');
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle).toHaveAttribute('data-state', 'light'));
    expect(container.querySelector('svg')).toHaveClass('lucide-sun');
    expect(icons.darkTheme).toBeTruthy();
    expect(icons.lightTheme).toBeTruthy();
  });

  it('brings hover, focus and press to the accent and nothing else to it', () => {
    renderToggle();
    const toggle = screen.getByRole('button');
    // At rest the control stays on the secondary rung: the accent is reserved.
    expect(toggle).toHaveClass('text-[var(--color-text-secondary)]');
    expect(toggle.className).not.toMatch(/bg-\[var\(--color-accent\)\]/);
    // The three live states all resolve to the accent.
    expect(toggle).toHaveClass('hover:text-[var(--color-accent-foreground)]');
    expect(toggle).toHaveClass('active:bg-[var(--color-accent-subtle)]', 'active:text-[var(--color-accent-foreground)]');
    expect(toggle).toHaveClass('focus-visible:outline-none', 'focus-visible:shadow-[var(--focus-ring)]');
    // Hover fills with a surface rung, so it does not read as a selection.
    expect(toggle).toHaveClass('hover:bg-[var(--color-bg-surface-2)]');
    // The ring is the shared two-layer one: a page-coloured gap then the accent.
    expect(css).toMatch(/--focus-ring:[^;]*var\(--color-bg-page\)[^;]*var\(--color-accent-foreground\)/);
  });

  it('keeps the 44px floor and a name that states the mode', async () => {
    renderToggle();
    const toggle = screen.getByRole('button');
    expect(toggle.className).toMatch(/\bmin-h-11\b/);
    expect(toggle.className).toMatch(/\bmin-w-11\b/);
    // The name states the mode the control is in, which is the only way a
    // screen reader user learns the current theme without seeing the glyph.
    await waitFor(() => {
      const state = toggle.getAttribute('data-state');
      expect(state === 'dark' || state === 'light').toBe(true);
      expect(toggle.getAttribute('aria-label')).toBe(`当前为${state === 'dark' ? '深色' : '浅色'}模式，点击切换`);
    });
  });
});

describe('token discipline across the overlay layer', () => {
  it('spends no hex, no rgb and no Tailwind palette utility', () => {
    for (const file of OVERLAY_FILES) {
      const code = sourceOf(file)
        .split('\n')
        .map(line => line.replace(/\/\/.*$/, ''))
        .join('\n');
      expect(code, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(code, file).not.toMatch(/\brgba?\(/);
      expect(code, file).not.toMatch(
        /\b(?:bg|text|border|ring|shadow|fill|stroke|outline|divide|from|via|to|placeholder)-(?:red|blue|green|teal|cyan|slate|gray|zinc|neutral|stone|amber|yellow|violet|purple|pink|rose|indigo|emerald|lime|orange|fuchsia|sky)-\d{2,3}\b/,
      );
    }
  });

  it('spends radius, shadow and font size on tokens, and no gradient anywhere', () => {
    for (const file of OVERLAY_FILES) {
      // The prose in these files is allowed to use the words; the class names
      // are not, so the scan drops comments and blanks out every `var()` body
      // before it looks at a value. Otherwise `--shadow-lg` inside a token
      // reference would read as a raw `shadow-lg` step.
      const code = sourceOf(file)
        .split('\n')
        .map(line => line.replace(/\/\/.*$/, ''))
        .join('\n')
        .replace(/var\(--[a-z0-9-]+\)/g, 'var(token)');
      expect(code, file).not.toMatch(/\brounded-(?:sm|md|lg|xl|2xl|3xl|full)\b/);
      expect(code, file).not.toMatch(/\bshadow-(?:sm|md|lg|xl|2xl|inner|none)\b/);
      expect(code, file).not.toMatch(/bg-gradient-to|bg-linear-to/);
      // Every rounded and shadow value resolves through a var().
      for (const match of sourceOf(file).matchAll(/\brounded-\[([^\]]+)\]/g)) {
        expect(match[1], file).toMatch(/^var\(--radius-/);
      }
      for (const match of sourceOf(file).matchAll(/\bshadow-\[([^\]]+)\]/g)) {
        // A lift resolves through a `--shadow-*` rung, and a focus indicator
        // through the two-layer `--focus-ring`, which is itself a box-shadow.
        expect(match[1], file).toMatch(/^var\(--(?:shadow-|focus-ring\))/);
      }
      for (const match of sourceOf(file).matchAll(/\btext-\[([^\]]+)\]/g)) {
        const value = match[1]!;
        // An arbitrary `text-[...]` is either a font-size rung or a colour, and
        // both have to arrive through a var().
        expect(value, file).toMatch(/^var\(--/);
        if (!value.startsWith('var(--color-')) {
          expect(value, file).toMatch(/^var\(--(?:text|icon|leading)-/);
        }
      }
    }
  });

  it('resolves every token the overlay layer names, in both themes', () => {
    const declared = new Set([...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map(match => match[1]!));
    const lightStart = css.indexOf('[data-theme="light"] {');
    const lightEnd = css.indexOf('\n}', lightStart);
    const lightDeclared = new Set(
      [...css.slice(lightStart, lightEnd).matchAll(/(--[a-z0-9-]+)\s*:/g)].map(match => match[1]!),
    );
    for (const file of OVERLAY_FILES) {
      const source = sourceOf(file);
      for (const match of source.matchAll(/var\((--[a-z0-9-]+)\)/g)) {
        expect(declared.has(match[1]!), `${file} ${match[1]}`).toBe(true);
      }
      // A colour a control paints with has to be restated for the light theme,
      // or switching themes leaves the dark value on screen.
      for (const match of source.matchAll(/(?:bg|text|border)-\[var\((--color-[\w-]+)\)\]/g)) {
        expect(lightDeclared.has(match[1]!), `${file} ${match[1]} in light`).toBe(true);
      }
    }
  });

  it('resolves the spacing and radius an overlay rung names', () => {
    for (const spec of Object.values(MODAL_DEPTHS)) {
      for (const value of Object.values(spec)) {
        for (const match of value.matchAll(/var\((--[a-z0-9-]+)\)/g)) {
          expect(css, match[1]).toMatch(new RegExp(`${match[1]}\\s*:`));
        }
      }
    }
  });
});
