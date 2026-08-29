import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Dialog, DialogDescription, DialogTitle } from '../Dialog';

function DialogHarness() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>打开</button>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>确认操作</DialogTitle>
        <DialogDescription>此操作需要确认。</DialogDescription>
        <button type="button">确认</button>
      </Dialog>
    </>
  );
}

describe('Dialog', () => {
  it('associates its title and description with the dialog', async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);

    await user.click(screen.getByRole('button', { name: '打开' }));

    expect(screen.getByRole('dialog', { name: '确认操作', description: '此操作需要确认。' })).toBeInTheDocument();
  });

  it('traps focus and restores it to the trigger after closing', async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    const trigger = screen.getByRole('button', { name: '打开' });

    await user.click(trigger);
    const closeButton = screen.getByRole('button', { name: '关闭' });
    const confirmButton = screen.getByRole('button', { name: '确认' });
    expect(closeButton).toHaveFocus();

    confirmButton.focus();
    await user.tab();
    expect(closeButton).toHaveFocus();

    closeButton.focus();
    await user.tab({ shift: true });
    expect(confirmButton).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
