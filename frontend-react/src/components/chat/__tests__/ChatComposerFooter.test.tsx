import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChatComposerFooter } from '../ChatComposerFooter';

describe('ChatComposerFooter', () => {
  it('shows the send/newline shortcut hints when the composer is empty', () => {
    render(<ChatComposerFooter hasDraft={false} />);
    const footer = screen.getByTestId('chat-composer-footer');
    expect(footer).toHaveTextContent('Enter');
    expect(footer).toHaveTextContent('Shift+Enter');
  });

  it('hides the shortcut hints once a draft exists, keeping the trailing slot', () => {
    render(
      <ChatComposerFooter hasDraft trailing={<span>Plan mode</span>} />,
    );
    const footer = screen.getByTestId('chat-composer-footer');
    expect(footer).not.toHaveTextContent('Enter');
    expect(footer).toHaveTextContent('Plan mode');
  });
});
