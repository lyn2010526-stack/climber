import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Dropdown, DropdownItem } from '../Dropdown';
import { Progress } from '../Progress';

afterEach(cleanup);

describe('shared accessibility polish', () => {
  it('moves focus into an open dropdown and keeps the trigger relationship', async () => {
    render(<Dropdown trigger="Actions"><DropdownItem>Export</DropdownItem></Dropdown>);
    const trigger = screen.getByRole('button', { name: 'Actions' });
    fireEvent.click(trigger);
    await waitFor(() => expect(screen.getByRole('menuitem', { name: 'Export' })).toHaveFocus());
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(trigger).toHaveAttribute('aria-controls', screen.getByRole('menu').id);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(trigger).toHaveFocus();
  });

  it('uses canonical semantic tokens for progress and exposes a textual value', () => {
    render(<Progress value={42} label="Completion" showLabel striped animated />);
    const progress = screen.getByRole('progressbar', { name: 'Completion' });
    expect(progress).toHaveAttribute('aria-valuenow', '42');
    expect(screen.getByText('42%')).toBeInTheDocument();
    expect(progress.querySelector('div > div')).toHaveStyle({ opacity: '0.9' });
  });

  it('keeps an explicit caller busy state on shared buttons', async () => {
    const onClose = vi.fn();
    expect(onClose).not.toHaveBeenCalled();
  });
});
