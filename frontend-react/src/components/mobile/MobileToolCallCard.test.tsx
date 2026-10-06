import { describe, it, expect, beforeAll } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import i18n from '../../i18n';
import { MobileToolCallCard } from './MobileToolCallCard';
import type { ToolCall } from '../../useChat';

beforeAll(async () => {
  await i18n.changeLanguage('zh-CN');
});

function tool(overrides: Partial<ToolCall>): ToolCall {
  return { id: 't1', name: 'read_file', arguments: { path: 'test.ts' }, ...overrides };
}

describe('MobileToolCallCard', () => {
  it('marks a running call and spins its glyph', () => {
    render(<MobileToolCallCard tool={tool({ status: 'running' })} />);
    const card = screen.getByText('read_file').closest('[data-tool-call]') as HTMLElement;
    expect(card.dataset.toolStatus).toBe('running');
    expect(screen.getByText('运行中')).toBeInTheDocument();
  });

  it('marks a successful call and keeps its result collapsed until expanded', () => {
    render(<MobileToolCallCard tool={tool({ status: 'success', result: '文件内容' })} />);
    expect(screen.getByText('完成')).toBeInTheDocument();
    // Collapsed content stays in the tree behind a 0fr grid row; expanding
    // animates the row open instead of remounting the payload.
    const body = document.getElementById(screen.getByRole('button', { name: /read_file/ }).getAttribute('aria-controls')!)!;
    expect(body.style.gridTemplateRows).toBe('0fr');
    fireEvent.click(screen.getByRole('button', { name: /read_file/ }));
    expect(body.style.gridTemplateRows).toBe('1fr');
    expect(screen.getByText('文件内容')).toBeInTheDocument();
    expect(screen.getByText(/"path": "test\.ts"/)).toBeInTheDocument();
  });

  it('surfaces an errored call in the error state with the detail', () => {
    render(<MobileToolCallCard tool={tool({ status: 'error', error: '读取失败' })} />);
    expect(screen.getByText('失败')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /read_file/ }));
    expect(screen.getByText('读取失败')).toBeInTheDocument();
  });

  it('reads an unreported historical call as not reported, never as failed', () => {
    render(<MobileToolCallCard tool={tool({})} />);
    const card = screen.getByText('read_file').closest('[data-tool-call]') as HTMLElement;
    expect(card.dataset.toolStatus).toBe('unknown');
    expect(screen.getByText('待报告')).toBeInTheDocument();
  });

  it('marks a stopped run as cancelled, distinct from a failure', () => {
    render(<MobileToolCallCard tool={tool({ status: 'cancelled' as never })} />);
    expect(screen.getByText('已取消')).toBeInTheDocument();
  });
});
