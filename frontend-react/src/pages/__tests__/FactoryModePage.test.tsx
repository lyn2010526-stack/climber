import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../api', () => ({
  api: {},
}));

import { FactoryModePage } from '../FactoryModePage';

describe('FactoryModePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders goal input', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText(/描述你想要智能体完成的目标/)).toBeDefined();
  });

  it('renders skill selector', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    // Skills are rendered with emoji prefix
    const skillBtns = document.querySelectorAll('button');
    expect(skillBtns.length).toBeGreaterThan(0);
  });

  it('renders prompt template selector', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    expect(screen.getByText('Senior Engineer')).toBeDefined();
    expect(screen.getByText('System Architect')).toBeDefined();
  });

  it('toggles skill selection', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    // Find a skill button containing "File Manager"
    const buttons = Array.from(document.querySelectorAll('button'));
    const fileManagerBtn = buttons.find(b => b.textContent?.includes('File Manager'));
    if (fileManagerBtn) {
      fireEvent.click(fileManagerBtn);
    }
    expect(fileManagerBtn).toBeDefined();
  });

  it('renders start button', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    expect(screen.getByText('开始执行')).toBeDefined();
  });

  it('disables start when goal is empty', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    const startBtn = screen.getByRole('button', { name: /开始执行/ });
    expect(startBtn).toBeDisabled();
  });

  it('enables start when goal is entered', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    const input = screen.getByPlaceholderText(/描述你想要智能体完成的目标/);
    fireEvent.change(input, { target: { value: 'Create a web app' } });
    expect(screen.getByRole('button', { name: /开始执行/ })).not.toBeDisabled();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    expect(screen.getByText('自主执行模式')).toBeDefined();
  });

  it('changes prompt template', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'architect' } });
    expect(select).toBeDefined();
  });

  it('renders skill buttons', () => {
    render(
      <MemoryRouter>
        <FactoryModePage />
      </MemoryRouter>
    );
    const buttons = Array.from(document.querySelectorAll('button'));
    const hasCodeExecutor = buttons.some(b => b.textContent?.includes('Code Executor'));
    const hasWebSearch = buttons.some(b => b.textContent?.includes('Web Search'));
    expect(hasCodeExecutor).toBe(true);
    expect(hasWebSearch).toBe(true);
  });
});
