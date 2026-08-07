import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemberConfig } from '../MemberConfig';

describe('MemberConfig', () => {
  const mockMembers = [
    {
      id: '1',
      name: 'Agent 1',
      provider: 'openai',
      modelId: 'gpt-4',
      apiKey: '',
      role: 'worker' as const,
      tools: ['web_search'],
    },
  ];

  it('renders without crashing', () => {
    const { container } = render(
      <MemberConfig
        members={mockMembers}
        onAdd={() => {}}
        onRemove={() => {}}
        onUpdate={() => {}}
      />
    );
    expect(container).toBeDefined();
  });

  it('renders members count', () => {
    render(
      <MemberConfig
        members={mockMembers}
        onAdd={() => {}}
        onRemove={() => {}}
        onUpdate={() => {}}
      />
    );
    expect(screen.getByText('AI 成员 (1)')).toBeDefined();
  });

  it('renders add button', () => {
    const { container } = render(
      <MemberConfig
        members={mockMembers}
        onAdd={() => {}}
        onRemove={() => {}}
        onUpdate={() => {}}
      />
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('calls onAdd when add button is clicked', () => {
    const onAdd = vi.fn();
    const { container } = render(
      <MemberConfig
        members={mockMembers}
        onAdd={onAdd}
        onRemove={() => {}}
        onUpdate={() => {}}
      />
    );
    const buttons = container.querySelectorAll('button');
    if (buttons.length > 0) {
      fireEvent.click(buttons[0]);
    }
    expect(onAdd).toHaveBeenCalled();
  });

  it('renders member name', () => {
    render(
      <MemberConfig
        members={mockMembers}
        onAdd={() => {}}
        onRemove={() => {}}
        onUpdate={() => {}}
      />
    );
    expect(screen.getByDisplayValue('Agent 1')).toBeDefined();
  });

  it('renders empty members', () => {
    const { container } = render(
      <MemberConfig
        members={[]}
        onAdd={() => {}}
        onRemove={() => {}}
        onUpdate={() => {}}
      />
    );
    expect(screen.getByText('AI 成员 (0)')).toBeDefined();
  });
});
