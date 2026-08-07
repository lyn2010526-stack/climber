import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ModelSelector, type ModelInfo } from '../ModelSelector';

const mockModels: ModelInfo[] = [
  {
    id: 'gpt-4',
    name: 'GPT-4 Turbo',
    provider: 'OpenAI',
    capabilities: ['chat', 'code', 'vision', 'tools'],
    contextWindow: 128000,
    status: 'available',
    latency: 120,
  },
  {
    id: 'claude-3',
    name: 'Claude 3 Opus',
    provider: 'Anthropic',
    capabilities: ['chat', 'code', 'reasoning'],
    contextWindow: 200000,
    status: 'busy',
    latency: 200,
  },
  {
    id: 'local-llama',
    name: 'Llama 3 70B',
    provider: 'Local',
    capabilities: ['chat', 'code'],
    contextWindow: 8192,
    status: 'offline',
  },
];

describe('ModelSelector', () => {
  it('renders selected model name', () => {
    render(
      <ModelSelector models={mockModels} selectedModel="gpt-4" onSelect={vi.fn()} />,
    );
    expect(screen.getByText('GPT-4 Turbo')).toBeDefined();
  });

  it('opens dropdown on click', () => {
    render(
      <ModelSelector models={mockModels} selectedModel="gpt-4" onSelect={vi.fn()} />,
    );
    fireEvent.click(screen.getByText('GPT-4 Turbo'));
    expect(screen.getByText('Claude 3 Opus')).toBeDefined();
    expect(screen.getByText('Llama 3 70B')).toBeDefined();
  });

  it('calls onSelect when a model is clicked', () => {
    const onSelect = vi.fn();
    render(
      <ModelSelector models={mockModels} selectedModel="gpt-4" onSelect={onSelect} />,
    );
    fireEvent.click(screen.getByText('GPT-4 Turbo'));
    fireEvent.click(screen.getByText('Claude 3 Opus'));
    expect(onSelect).toHaveBeenCalledWith('claude-3');
  });

  it('displays capability badges', () => {
    render(
      <ModelSelector models={mockModels} selectedModel="gpt-4" onSelect={vi.fn()} />,
    );
    fireEvent.click(screen.getByText('GPT-4 Turbo'));
    expect(screen.getAllByText('对话').length).toBeGreaterThan(0);
    expect(screen.getAllByText('代码').length).toBeGreaterThan(0);
    expect(screen.getByText('视觉')).toBeDefined();
  });

  it('displays status indicators', () => {
    render(
      <ModelSelector models={mockModels} selectedModel="gpt-4" onSelect={vi.fn()} />,
    );
    fireEvent.click(screen.getByText('GPT-4 Turbo'));
    expect(screen.getByText('可用')).toBeDefined();
    expect(screen.getByText('繁忙')).toBeDefined();
    expect(screen.getByText('离线')).toBeDefined();
  });
});
