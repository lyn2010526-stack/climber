import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SessionExportMenu } from '../SessionExportMenu';

const mockMessages = [
  { id: '1', role: 'user' as const, content: 'Hello', timestamp: 1704067200000 },
  { id: '2', role: 'assistant' as const, content: 'Hi there!', timestamp: 1704067260000 },
];

describe('SessionExportMenu', () => {
  it('renders export button', () => {
    render(<SessionExportMenu messages={mockMessages} sessionTitle="Test Chat" />);
    expect(screen.getByText('导出')).toBeDefined();
  });

  it('opens menu on click', () => {
    render(<SessionExportMenu messages={mockMessages} sessionTitle="Test Chat" />);
    fireEvent.click(screen.getByText('导出'));
    expect(screen.getByText('Markdown')).toBeDefined();
    expect(screen.getByText('JSON')).toBeDefined();
    expect(screen.getByText('纯文本')).toBeDefined();
    expect(screen.getByText('复制全部')).toBeDefined();
  });

  it('displays format descriptions', () => {
    render(<SessionExportMenu messages={mockMessages} sessionTitle="Test Chat" />);
    fireEvent.click(screen.getByText('导出'));
    expect(screen.getByText('格式化文档')).toBeDefined();
    expect(screen.getByText('结构化数据')).toBeDefined();
  });
});
