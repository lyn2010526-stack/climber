import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Modal, ConfirmDialog } from '../Modal';
import { Switch } from '../Switch';
import { Dropdown, DropdownItem, DropdownSubMenu } from '../Dropdown';
import { EmptyState } from '../EmptyState';
import { Skeleton } from '../Skeleton';
import { cardVariants } from '../Card';
import { icons, iconSizes } from '../../../lib/icons';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

afterEach(cleanup);

describe('shared controls task 09', () => {
  it('forwards modal refs, traps initial focus and restores focus and scroll on unmount', async () => {
    const ref = createRef<HTMLDivElement>();
    const { rerender, unmount } = render(<button>Open</button>);
    const opener = screen.getByRole('button');
    opener.focus();
    document.body.style.overflow = 'auto';
    rerender(<><button>Open</button><Modal ref={ref} open title="Settings" description="Preferences" showClose={false} onClose={vi.fn()}><button disabled>Unavailable</button><button>Save</button><button>Cancel</button></Modal></>);
    await waitFor(() => expect(ref.current).toHaveFocus());
    expect(screen.getByRole('dialog')).toHaveAccessibleName('Settings');
    expect(screen.getByRole('dialog')).toHaveAccessibleDescription('Preferences');
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(screen.getByRole('button', { name: 'Save' })).toHaveFocus();
    rerender(<button>Open</button>);
    expect(screen.getByRole('button')).toHaveFocus();
    expect(document.body.style.overflow).toBe('auto');
    expect(ref.current).toBeNull();
    unmount();
    document.body.style.overflow = '';
  });

  it('respects overlay and Escape dismissal options', () => {
    const onClose = vi.fn();
    const { rerender } = render(<Modal open title="Settings" onClose={onClose}>Content</Modal>);
    fireEvent.click(screen.getByText('Content'));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(document.querySelector('[data-modal-overlay]')!);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
    rerender(<Modal open title="Settings" onClose={onClose} closeOnOverlay={false} closeOnEsc={false} />);
    fireEvent.click(document.querySelector('[data-modal-overlay]')!);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('keeps confirmation labels and pending semantics stable', () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open title="Delete" confirmText="Delete item" loading onConfirm={onConfirm} onClose={vi.fn()} />);
    const confirm = screen.getByRole('button', { name: 'Delete item' });
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    fireEvent.click(confirm);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('associates switch labels and descriptions while preserving controlled state', () => {
    const onChange = vi.fn();
    const { rerender } = render(<Switch label="Notifications" description="Task updates" checked={false} onChange={onChange} />);
    const control = screen.getByRole('switch', { name: 'Notifications' });
    expect(control).toHaveAccessibleDescription('Task updates');
    fireEvent.click(control);
    expect(onChange).toHaveBeenCalledWith(true);
    expect(control).toHaveAttribute('aria-checked', 'false');
    rerender(<Switch label="Notifications" checked disabled onChange={onChange} />);
    fireEvent.click(control);
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(control).toHaveAttribute('aria-checked', 'true');
  });

  it('keeps submenus open on activation and closes only on enabled selection', () => {
    const onOpenChange = vi.fn();
    render(<Dropdown trigger="Actions" onOpenChange={onOpenChange}><DropdownSubMenu trigger="More"><DropdownItem>Export</DropdownItem></DropdownSubMenu><DropdownItem disabled>Disabled</DropdownItem></Dropdown>);
    fireEvent.click(screen.getByRole('button', { name: 'Actions' }));
    fireEvent.click(screen.getByRole('menuitem', { name: 'More' }));
    expect(screen.getByRole('menuitem', { name: 'Export' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('menuitem', { name: 'Disabled' }));
    expect(onOpenChange).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('menuitem', { name: 'Export' }));
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
  });

  it('uses four icon sizes and only maps consumed shared meanings', () => {
    expect(iconSizes).toEqual({ xs: 12, sm: 14, md: 16, lg: 20 });
    const directory = resolve(process.cwd(), 'src/components/ui');
    const source = readdirSync(directory).filter(file => file.endsWith('.tsx')).map(file => readFileSync(resolve(directory, file), 'utf8')).join('\n');
    for (const name of Object.keys(icons)) expect(source).toContain(`icons.${name}`);
    expect(source).not.toMatch(/\p{Extended_Pictographic}/u);
    expect(source).not.toMatch(/backdrop-blur|hover:-translate|bg-gradient-to/);
    for (const variant of ['glass', 'gradient', 'elevated'] as const) {
      expect(cardVariants({ variant })).toContain('bg-[var(--color-bg-surface-1)]');
    }
  });

  it('keeps custom empty-state content while hiding built-in decorative icons', () => {
    const { container, rerender } = render(<EmptyState title="No files" icon="file" />);
    expect(container.querySelector('svg')).toHaveAttribute('width', String(iconSizes.lg));
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    rerender(<EmptyState title="No files" illustration={<span>Custom content</span>} action={<button>Create</button>} />);
    expect(screen.getByText('Custom content')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create' })).toBeInTheDocument();
    rerender(<Skeleton animated={false} width={100} />);
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
    expect(container.firstChild).not.toHaveClass('animate-pulse');
  });
});
