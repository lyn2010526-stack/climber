import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { setTypewriterMode } from './typewriterConfig';
import { TypewriterModeToggle } from './TypewriterModeToggle';

beforeEach(async () => {
  setTypewriterMode('off');
  localStorage.clear();
  await i18n.changeLanguage('zh-CN');
});

describe('TypewriterModeToggle', () => {
  it('starts at off and exposes a pressed state only for active presets', () => {
    render(<TypewriterModeToggle />);
    expect(screen.getByTestId('typewriter-mode-toggle')).toHaveAttribute('data-typewriter-mode', 'off');
    expect(screen.getByTestId('typewriter-mode-toggle')).toHaveAttribute('aria-pressed', 'false');
  });

  it('cycles through balanced, realtime and silky on each click', async () => {
    const user = userEvent.setup();
    render(<TypewriterModeToggle />);
    const toggle = screen.getByTestId('typewriter-mode-toggle');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('data-typewriter-mode', 'balanced');
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('data-typewriter-mode', 'realtime');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('data-typewriter-mode', 'silky');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('data-typewriter-mode', 'off');
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
  });
});