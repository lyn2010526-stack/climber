import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MemoryPage from '../MemoryPage';

describe('MemoryPage', () => {
  it('renders page title', () => {
    render(<MemoryPage />);
    expect(screen.getByText('记忆管理')).toBeDefined();
  });

  it('renders description', () => {
    render(<MemoryPage />);
    expect(screen.getByText('Agent 记忆系统的四层架构')).toBeDefined();
  });

  it('renders L1 memory card', () => {
    render(<MemoryPage />);
    expect(screen.getByText('工作记忆')).toBeDefined();
  });

  it('renders L2 memory card', () => {
    render(<MemoryPage />);
    expect(screen.getByText('情景记忆')).toBeDefined();
  });

  it('renders L3 memory card', () => {
    render(<MemoryPage />);
    expect(screen.getByText('语义记忆')).toBeDefined();
  });

  it('renders L4 memory card', () => {
    render(<MemoryPage />);
    expect(screen.getByText('身份记忆')).toBeDefined();
  });
});
