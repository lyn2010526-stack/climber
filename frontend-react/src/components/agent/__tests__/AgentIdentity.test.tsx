import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentIdentity } from '../AgentIdentity';

describe('AgentIdentity', () => {
  it('renders without crashing', () => {
    const { container } = render(<AgentIdentity />);
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(<AgentIdentity />);
    expect(screen.getByText('智能体身份')).toBeDefined();
  });

  it('renders agent names', () => {
    render(<AgentIdentity />);
    expect(screen.getAllByText('代码助手').length).toBeGreaterThan(0);
    expect(screen.getAllByText('架构顾问').length).toBeGreaterThan(0);
  });

  it('renders active agent details', () => {
    render(<AgentIdentity />);
    expect(screen.getByText('专业的软件工程师，擅长编写高质量代码，遵循最佳实践和设计模式。')).toBeDefined();
  });

  it('renders goals', () => {
    render(<AgentIdentity />);
    expect(screen.getByText('帮助开发者编写高质量代码')).toBeDefined();
  });

  it('switches active agent on click', () => {
    render(<AgentIdentity />);
    fireEvent.click(screen.getByText('架构顾问'));
    expect(screen.getByText('资深系统架构师，专注于系统设计、技术选型和性能优化。')).toBeDefined();
  });

  it('enters edit mode when edit button clicked', () => {
    render(<AgentIdentity />);
    fireEvent.click(screen.getByText('编辑'));
    expect(screen.getByText('保存')).toBeDefined();
    expect(screen.getByText('取消')).toBeDefined();
  });

  it('renders memory scope options in edit mode', () => {
    render(<AgentIdentity />);
    fireEvent.click(screen.getByText('编辑'));
    expect(screen.getByText('项目级')).toBeDefined();
    expect(screen.getByText('全局')).toBeDefined();
    expect(screen.getByText('会话级')).toBeDefined();
  });
});
