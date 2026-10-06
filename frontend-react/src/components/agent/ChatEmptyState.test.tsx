import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ChatEmptyState } from './ChatEmptyState';

describe('ChatEmptyState', () => {
  it('shows a four-point star, a title and the three example cards', () => {
    render(<ChatEmptyState onSend={vi.fn()} />);
    expect(screen.getByTestId('chat-empty-icon')).toHaveAttribute('data-workbench-icon', 'spark');
    expect(screen.getByRole('heading')).toBeVisible();
    const cards = screen.getAllByRole('button');
    expect(cards).toHaveLength(3);
  });

  it('sends the example label through onSend when a card is pressed', () => {
    const onSend = vi.fn();
    render(<ChatEmptyState onSend={onSend} />);
    fireEvent.click(screen.getByTestId('chat-example-code'));
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith(
      'Analyze this architecture and suggest improvements',
    );
  });

  it('uses caller-supplied examples verbatim', () => {
    const onSend = vi.fn();
    render(
      <ChatEmptyState
        onSend={onSend}
        examples={[
          { id: 'custom', label: 'Do the custom thing' },
          { id: 'other', label: 'And this one' },
        ]}
      />,
    );
    expect(screen.queryByTestId('chat-example-plan')).toBeNull();
    fireEvent.click(screen.getByTestId('chat-example-custom'));
    expect(onSend).toHaveBeenCalledWith('Do the custom thing');
  });

  it('renders examples as inert when disabled', () => {
    const onSend = vi.fn();
    render(<ChatEmptyState onSend={onSend} disabled />);
    const card = screen.getByTestId('chat-example-plan');
    expect(card).toBeDisabled();
    fireEvent.click(card);
    expect(onSend).not.toHaveBeenCalled();
  });

  it('honours a caller-supplied icon and title instead of the defaults', () => {
    render(
      <ChatEmptyState
        title="Custom title"
        icon={<span data-testid="custom-icon" />}
        onSend={vi.fn()}
      />,
    );
    expect(screen.getByRole('heading')).toHaveTextContent('Custom title');
    expect(screen.getByTestId('custom-icon')).toBeVisible();
    expect(screen.queryByTestId('chat-empty-icon')).toBeNull();
  });

  it('keeps extra actions below the example list', () => {
    render(
      <ChatEmptyState
        onSend={vi.fn()}
        actions={<button type="button">Extra</button>}
      />,
    );
    const list = screen.getByRole('list');
    expect(list.nextElementSibling).toHaveTextContent('Extra');
    expect(within(list).getAllByRole('listitem')).toHaveLength(3);
  });
});
