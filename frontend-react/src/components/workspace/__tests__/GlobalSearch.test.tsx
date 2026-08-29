import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { GlobalSearch } from '../GlobalSearch';

describe('GlobalSearch', () => {
  it('focuses the search input and restores focus after closing', async () => {
    const user = userEvent.setup();
    function Harness() {
      const [isOpen, setIsOpen] = React.useState(false);
      return (
        <>
          <button type="button" onClick={() => setIsOpen(true)}>打开全局搜索</button>
          <GlobalSearch isOpen={isOpen} onClose={() => setIsOpen(false)} />
        </>
      );
    }

    render(<Harness />);
    const trigger = screen.getByRole('button', { name: '打开全局搜索' });
    await user.click(trigger);
    expect(screen.getByPlaceholderText('搜索文档、记忆、群组...')).toHaveFocus();

    await user.keyboard('{Escape}');
    expect(trigger).toHaveFocus();
  });

  it('labels filter controls for assistive technology', async () => {
    render(<GlobalSearch isOpen onClose={vi.fn()} />);

    expect(screen.getByRole('button', { name: '按全部筛选' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '按文档筛选' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '按记忆筛选' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '按群组筛选' })).toBeInTheDocument();
  });
});
