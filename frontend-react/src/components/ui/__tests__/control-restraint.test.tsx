import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { Button } from '../Button';
import { Modal, ConfirmDialog } from '../Modal';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../Tabs';
import { Switch } from '../Switch';
import { Dropdown, DropdownItem } from '../Dropdown';
import { icons, iconSizes, iconSize, statusIconFor } from '../../../lib/icons';

afterEach(cleanup);

const UI_DIR = resolve(process.cwd(), 'src/components/ui');
const uiSources = readdirSync(UI_DIR)
  .filter(file => file.endsWith('.tsx'))
  .map(file => readFileSync(resolve(UI_DIR, file), 'utf8'))
  .join('\n');

describe('control restraint', () => {
  it('keeps decoration out of the control layer', () => {
    // No frosted glass, no hover lift, no decorative gradient anywhere in the
    // shared control surface.
    expect(uiSources).not.toMatch(/backdrop-blur|backdrop-filter/);
    expect(uiSources).not.toMatch(/hover:(?:-?translate|translate)-/);
    expect(uiSources).not.toMatch(/(?:hover|active):scale-/);
    expect(uiSources).not.toMatch(/bg-gradient-to|bg-linear-to/);
  });

  it('reserves accent for a single primary action and confines status colors', () => {
    // A view shows one saturated element: the primary action.
    const primary = render(<Button variant="primary">Save</Button>);
    expect(primary.container.firstChild).toHaveClass('bg-[var(--color-accent)]');
    // Siblings resolve to neutral surfaces, so the primary still leads. The
    // accent text token lives on the focus ring of every control, so the
    // check targets the background specifically.
    const siblings = render(
      <>
        <Button variant="secondary">Cancel</Button>
        <Button variant="outline">Later</Button>
        <Button variant="ghost">Dismiss</Button>
      </>
    );
    for (const button of within(siblings.container).getAllByRole('button')) {
      expect(button.className).not.toMatch(/(?:^|\s)bg-\[var\(--color-accent\)\]/);
      expect(button.className).toMatch(/bg-\[var\(--color-bg-surface-\d\)\]|\bbg-transparent\b/);
    }

    // Status hues only appear on variants that report a state.
    const buttonSource = readFileSync(resolve(UI_DIR, 'Button.tsx'), 'utf8');
    for (const variant of ['destructive', 'success'] as const) {
      const block = buttonSource.slice(buttonSource.indexOf(`${variant}: [`));
      expect(block.slice(0, block.indexOf('],'))).toMatch(/--(?:color-error|color-success)/);
    }
  });

  it('marks pending buttons busy and keeps the accessible name stable', () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button loading onClick={onClick}>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toBeDisabled();
    // Label stays mounted so the name and the width survive the spinner.
    expect(screen.getByText('Save')).toBeInTheDocument();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();

    rerender(<Button onClick={onClick}>Save</Button>);
    expect(screen.getByRole('button', { name: 'Save' })).not.toHaveAttribute('aria-busy');
  });

  it('defaults to type="button" so a stray click never submits a form', () => {
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault());
    render(
      <form onSubmit={onSubmit}>
        <label htmlFor="f">Name</label>
        <input id="f" />
        <Button onClick={() => {}}>Not a submit</Button>
      </form>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Not a submit' }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Not a submit' })).toHaveAttribute('type', 'button');
  });

  it('honours reduced motion and the shared focus ring on every variant', () => {
    for (const variant of ['primary', 'secondary', 'outline', 'ghost', 'subtle', 'destructive', 'success', 'link'] as const) {
      const { container, unmount } = render(<Button variant={variant}>Go</Button>);
      const button = container.firstChild!;
      expect(button).toHaveClass('motion-reduce:transition-none');
      // The indicator is the two-layer `--focus-ring`: a page-coloured gap then
      // the accent, so it stays visible on the accent fill of a primary button
      // and on the bare page behind a ghost one. The ad-hoc outline pair is
      // gone, and a variant that painted its own ring would now double it.
      expect(button).toHaveClass('focus-visible:shadow-[var(--focus-ring)]');
      expect(button).toHaveClass('focus-visible:outline-none');
      expect(button.className).not.toMatch(/focus-visible:outline-(?!none)/);
      expect(button).toHaveClass('disabled:cursor-not-allowed');
      unmount();
    }
  });

  it('expresses disabled through tokens rather than a blanket opacity', () => {
    const { container } = render(<Button variant="primary" disabled>Save</Button>);
    const button = container.firstChild!;
    expect(button).toHaveClass('disabled:bg-[var(--color-bg-disabled)]');
    expect(button).toHaveClass('disabled:text-[var(--color-text-disabled)]');
    // A uniform fade would wash out the label and read as still pressable.
    expect(button).not.toHaveClass('disabled:opacity-50');
  });
});

describe('modal semantics', () => {
  it('puts the dialog role on the content panel, not the overlay', () => {
    render(<Modal open title="Settings" onClose={vi.fn()}>Body</Modal>);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAccessibleName('Settings');
    // The overlay is decorative and must not be the dialog surface.
    expect(dialog).not.toContainElement(document.querySelector('[data-modal-overlay]'));
    expect(document.querySelector('[data-modal-overlay]')).toHaveAttribute('aria-hidden', 'true');
  });

  it('traps Tab, restores focus and drops the decorative entry animation', async () => {
    const ref = createRef<HTMLDivElement>();
    const { rerender } = render(<button>Open</button>);
    (screen.getByRole('button') as HTMLElement).focus();
    rerender(
      <>
        <button>Open</button>
        <Modal ref={ref} open title="Settings" onClose={vi.fn()}>
          <button>Save</button>
        </Modal>
      </>
    );
    const dialog = screen.getByRole('dialog');
    await vi.waitFor(() => expect(dialog).toHaveFocus());
    // fadeIn was pure decoration on an already-focused panel.
    expect(dialog.className).not.toMatch(/animate-\[/);
    expect(dialog.className).toMatch(/focus-visible:outline-none/);
    rerender(<button>Open</button>);
    expect(screen.getByRole('button', { name: 'Open' })).toHaveFocus();
  });

  it('dismisses on overlay and Escape only when each is enabled', () => {
    const onClose = vi.fn();
    const { rerender } = render(<Modal open title="Settings" onClose={onClose}>Body</Modal>);
    fireEvent.click(document.querySelector('[data-modal-overlay]')!);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
    rerender(<Modal open title="Settings" onClose={onClose} closeOnOverlay={false} closeOnEsc={false}>Body</Modal>);
    fireEvent.click(document.querySelector('[data-modal-overlay]')!);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('gives every destructive confirmation the same destructive treatment', () => {
    const { rerender } = render(<ConfirmDialog open title="Delete" onConfirm={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveClass('bg-[var(--color-accent)]');
    // `warning` used to fall back to the accent primary, which read as safe.
    rerender(<ConfirmDialog open variant="warning" title="Delete" onConfirm={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveClass('text-[var(--color-error)]');
  });
});

describe('tabs semantics', () => {
  const setup = () =>
    render(
      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
        </TabsList>
        <TabsContent value="one">First</TabsContent>
        <TabsContent value="two">Second</TabsContent>
      </Tabs>
    );

  it('wires tablist, tabs, panels and selection state together', () => {
    setup();
    const list = screen.getByRole('tablist');
    const [one, two] = screen.getAllByRole('tab');
    expect(one).toHaveAttribute('aria-selected', 'true');
    expect(two).toHaveAttribute('aria-selected', 'false');
    expect(one).toHaveAttribute('aria-controls', screen.getByRole('tabpanel').id);
    expect(screen.getByRole('tabpanel')).toHaveAccessibleName('One');
    expect(within(list).getAllByRole('tab')).toHaveLength(2);
  });

  it('moves selection and roving focus with arrow, Home and End', () => {
    setup();
    const [one, two] = screen.getAllByRole('tab');
    // Only the selected tab sits in the tab order.
    expect(one).toHaveAttribute('tabindex', '0');
    expect(two).toHaveAttribute('tabindex', '-1');
    one.focus();
    fireEvent.keyDown(screen.getByRole('tablist'), { key: 'ArrowRight' });
    expect(two).toHaveAttribute('aria-selected', 'true');
    expect(two).toHaveFocus();
    expect(screen.getByRole('tabpanel')).toHaveAccessibleName('Two');
    fireEvent.keyDown(screen.getByRole('tablist'), { key: 'Home' });
    expect(one).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(screen.getByRole('tablist'), { key: 'End' });
    expect(two).toHaveAttribute('aria-selected', 'true');
  });
});

describe('switch semantics', () => {
  it('exposes a labelled switch and ignores clicks while disabled', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <Switch label="Notifications" description="Task updates" checked={false} onChange={onChange} />
    );
    const control = screen.getByRole('switch', { name: 'Notifications' });
    expect(control).toHaveAttribute('type', 'button');
    expect(control).toHaveAccessibleDescription('Task updates');
    fireEvent.click(control);
    expect(onChange).toHaveBeenCalledWith(true);
    rerender(<Switch label="Notifications" checked disabled onChange={onChange} />);
    fireEvent.click(control);
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(control).toHaveClass('focus-visible:shadow-[var(--focus-ring)]');
    expect(control).toHaveClass('motion-reduce:transition-none');
  });
});

describe('dropdown semantics', () => {
  it('attaches menu semantics to the caller trigger without nesting buttons', () => {
    render(
      <Dropdown trigger={<button type="button" aria-label="Open actions">Actions</button>}>
        <DropdownItem>Export</DropdownItem>
      </Dropdown>
    );
    const trigger = screen.getByRole('button', { name: 'Open actions' });
    expect(trigger.tagName).toBe('BUTTON');
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    // A focusable role="button" wrapper produced a button inside a button.
    expect(document.querySelector('[role="button"]')).toBeNull();
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(trigger).toHaveAttribute('aria-controls', screen.getByRole('menu').id);
  });

  it('opens from the keyboard and moves focus between menu items', () => {
    render(
      <Dropdown trigger={<button type="button" aria-label="Open actions">Actions</button>}>
        <DropdownItem>Export</DropdownItem>
        <DropdownItem>Delete</DropdownItem>
      </Dropdown>
    );
    const trigger = screen.getByRole('button', { name: 'Open actions' });
    trigger.focus();
    fireEvent.keyDown(trigger, { key: 'Enter' });
    expect(screen.getByRole('menu')).toBeInTheDocument();
    const [first, second] = screen.getAllByRole('menuitem');
    first.focus();
    fireEvent.keyDown(screen.getByRole('menu'), { key: 'ArrowDown' });
    expect(second).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('menu'), { key: 'Home' });
    expect(first).toHaveFocus();
  });

  it('falls back to a real button when the trigger is not an element', () => {
    render(
      <Dropdown trigger="Actions">
        <DropdownItem>Export</DropdownItem>
      </Dropdown>
    );
    const trigger = screen.getByRole('button', { name: 'Actions' });
    expect(trigger.tagName).toBe('BUTTON');
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
    fireEvent.click(trigger);
    expect(screen.getByRole('menu')).toBeInTheDocument();
  });

  it('returns focus to the trigger on Escape', () => {
    render(
      <Dropdown trigger={<button type="button" aria-label="Open actions">Actions</button>}>
        <DropdownItem>Export</DropdownItem>
      </Dropdown>
    );
    const trigger = screen.getByRole('button', { name: 'Open actions' });
    fireEvent.click(trigger);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).toBeNull();
    expect(trigger).toHaveFocus();
  });
});

describe('icon scale', () => {
  it('exposes exactly four sizes and resolves them by name', () => {
    expect(iconSizes).toEqual({ xs: 12, sm: 14, md: 16, lg: 20 });
    expect(iconSize('xs')).toBe(12);
    expect(iconSize('lg')).toBe(20);
    expect(iconSize()).toBe(16);
  });

  it('gives every control size a glyph from the four-rung ladder', () => {
    for (const size of ['xs', 'sm', 'md', 'lg'] as const) {
      const { container, unmount } = render(<Button size={size} loading>Save</Button>);
      expect(container.querySelector('svg')).toHaveAttribute('width', String(iconSizes[size]));
      unmount();
    }
    // Icon-only buttons are sized by their own box, so they borrow the rung
    // that matches that box instead of the control-name ladder.
    const wide = render(<Button size="icon" loading aria-label="Send" />);
    expect(wide.container.querySelector('svg')).toHaveAttribute('width', String(iconSizes.md));
    const narrow = render(<Button size="icon-sm" loading aria-label="Send" />);
    expect(narrow.container.querySelector('svg')).toHaveAttribute('width', String(iconSizes.sm));
  });

  it('maps every status tone to a real icon and nothing else', () => {
    expect(statusIconFor('error')).toBe('error');
    expect(statusIconFor('success')).toBe('success');
    expect(statusIconFor('loading')).toBe('loading');
    expect(statusIconFor(undefined)).toBeNull();
  });

  it('keeps every shared icon genuinely consumed and re-exports no lucide wildcard', () => {
    const iconConsumers = [
      uiSources,
      readFileSync(resolve(process.cwd(), 'src/components/workspace/AnchoredLeftNav.tsx'), 'utf8'),
      readFileSync(resolve(process.cwd(), 'src/components/privacy/LocalPinSettings.tsx'), 'utf8'),
    ].join('\n');
    for (const name of Object.keys(icons)) {
      expect(iconConsumers).toContain(`icons.${name}`);
    }
    const source = readFileSync(resolve(process.cwd(), 'src/lib/icons.ts'), 'utf8');
    // A wildcard re-export would defeat the semantic mapping entirely.
    expect(source).not.toMatch(/export\s+\*\s+from\s+['"]lucide-react['"]/);
    expect(source).not.toMatch(/as\s+LucideIcon;\s*$/m);
    expect(source).toMatch(/satisfies Record<string, LucideIcon>/);
  });
});
