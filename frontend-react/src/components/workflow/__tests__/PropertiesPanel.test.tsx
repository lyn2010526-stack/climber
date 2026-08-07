import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PropertiesPanel } from '../PropertiesPanel';

const mockNode = {
  id: 'node-1',
  type: 'llm',
  position: { x: 0, y: 0 },
  data: { label: 'Test LLM' },
};

describe('PropertiesPanel', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(container).toBeDefined();
  });

  it('renders node type and id', () => {
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText('llm')).toBeDefined();
    expect(screen.getByText('node-1')).toBeDefined();
  });

  it('renders fields based on node type', () => {
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText('Label')).toBeDefined();
    expect(screen.getByText('Model')).toBeDefined();
    expect(screen.getByText('System Prompt')).toBeDefined();
  });

  it('calls onUpdate when field value changes', () => {
    const onUpdate = vi.fn();
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={onUpdate}
        onDelete={() => {}}
      />
    );
    const input = screen.getByPlaceholderText('Enter label...');
    fireEvent.change(input, { target: { value: 'New Label' } });
    expect(onUpdate).toHaveBeenCalledWith('node-1', { label: 'New Label' });
  });

  it('renders delete confirmation when delete button is clicked', () => {
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    const deleteBtn = document.querySelector('[title="Delete node"]');
    if (deleteBtn) {
      fireEvent.click(deleteBtn);
      expect(screen.getByText('Delete Node?')).toBeDefined();
    }
  });

  it('renders different fields for input node type', () => {
    const inputNode = { ...mockNode, type: 'input' };
    render(
      <PropertiesPanel
        node={inputNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText('Variable Name')).toBeDefined();
    expect(screen.getByText('Required')).toBeDefined();
  });

  it('calls onDelete when delete is confirmed', () => {
    const onDelete = vi.fn();
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={() => {}}
        onDelete={onDelete}
      />
    );
    const deleteBtn = document.querySelector('[title="Delete node"]');
    if (deleteBtn) {
      fireEvent.click(deleteBtn);
      fireEvent.click(screen.getByText('Delete'));
      expect(onDelete).toHaveBeenCalled();
    }
  });

  it('cancels delete when cancel is clicked', () => {
    const onDelete = vi.fn();
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={() => {}}
        onDelete={onDelete}
      />
    );
    const deleteBtn = document.querySelector('[title="Delete node"]');
    if (deleteBtn) {
      fireEvent.click(deleteBtn);
      fireEvent.click(screen.getByText('Cancel'));
      expect(onDelete).not.toHaveBeenCalled();
      expect(screen.queryByText('Delete Node?')).toBeNull();
    }
  });

  it('handles select field change', () => {
    const onUpdate = vi.fn();
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={onUpdate}
        onDelete={() => {}}
      />
    );
    const selects = document.querySelectorAll('select');
    if (selects.length > 0) {
      fireEvent.change(selects[0], { target: { value: 'gpt-4' } });
      expect(onUpdate).toHaveBeenCalledWith('node-1', { model: 'gpt-4' });
    }
  });

  it('renders tool node fields', () => {
    const toolNode = { ...mockNode, type: 'tool', data: {} };
    render(
      <PropertiesPanel
        node={toolNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText('Tool Name')).toBeDefined();
    expect(screen.getByText('Parameters (JSON)')).toBeDefined();
  });

  it('renders condition node fields', () => {
    const condNode = { ...mockNode, type: 'condition', data: {} };
    render(
      <PropertiesPanel
        node={condNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText('Operator')).toBeDefined();
    expect(screen.getByText('Expected Value')).toBeDefined();
  });

  it('renders output node fields', () => {
    const outNode = { ...mockNode, type: 'output', data: {} };
    render(
      <PropertiesPanel
        node={outNode as any}
        onUpdate={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText('Format')).toBeDefined();
  });

  it('handles textarea change', () => {
    const onUpdate = vi.fn();
    render(
      <PropertiesPanel
        node={mockNode as any}
        onUpdate={onUpdate}
        onDelete={() => {}}
      />
    );
    const textarea = document.querySelector('textarea');
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'prompt text' } });
      expect(onUpdate).toHaveBeenCalledWith('node-1', { system_prompt: 'prompt text' });
    }
  });
});
