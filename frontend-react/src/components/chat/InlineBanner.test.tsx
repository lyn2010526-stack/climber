import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { InlineBanner } from './InlineBanner';

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('InlineBanner — codex actionable_banner 移植', () => {
  it('渲染粗体标题与普通描述行', () => {
    render(<InlineBanner title="工作区提示" description="检出了一条新分支" />);
    const title = screen.getByText('工作区提示');
    expect(title).toHaveClass('font-semibold');
    const description = screen.getByText('检出了一条新分支');
    expect(description).not.toHaveClass('font-semibold');
  });

  it('Actions 变体渲染编号列表，点击触发 onSelect', () => {
    const onSelect = vi.fn();
    render(
      <InlineBanner
        title="请选择"
        actions={[{ id: 'a', label: '继续' }, { id: 'b', label: '放弃' }]}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText('放弃'));
    expect(onSelect).toHaveBeenCalledWith('b');
    expect(screen.getByText('1.')).toBeInTheDocument();
    expect(screen.getByText('2.')).toBeInTheDocument();
  });

  it('可关闭：esc 触发 onDismiss 并隐藏', () => {
    const onDismiss = vi.fn();
    const { container } = render(<InlineBanner title="可关闭" onDismiss={onDismiss} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(container.querySelector('[role="status"]')).toBeNull();
  });

  it('persistent：esc 不关闭', () => {
    const onDismiss = vi.fn();
    render(<InlineBanner title="常驻" dismissal="persistent" onDismiss={onDismiss} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onDismiss).not.toHaveBeenCalled();
    expect(screen.getByText('常驻')).toBeInTheDocument();
  });

  it('数字键 1-9 选择对应动作', () => {
    const onSelect = vi.fn();
    render(
      <InlineBanner
        title="选择"
        actions={[{ id: 'x', label: '甲' }, { id: 'y', label: '乙' }]}
        onSelect={onSelect}
      />,
    );
    fireEvent.keyDown(document, { key: '2' });
    expect(onSelect).toHaveBeenCalledWith('y');
    // 超出可见数量时不触发。
    fireEvent.keyDown(document, { key: '9' });
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('目标是输入框时不吞键（输入可继续）', () => {
    const onDismiss = vi.fn();
    const onSelect = vi.fn();
    render(
      <div>
        <textarea data-testid="composer" />
        <InlineBanner
          title="提示"
          actions={[{ id: 'a', label: '动作' }]}
          onDismiss={onDismiss}
          onSelect={onSelect}
        />
      </div>,
    );
    const textarea = screen.getByTestId('composer');
    fireEvent.keyDown(textarea, { key: 'Escape' });
    fireEvent.keyDown(textarea, { key: '1' });
    expect(onDismiss).not.toHaveBeenCalled();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('提示文案按 dismissal × 有无动作 分四态', () => {
    const { rerender } = render(
      <InlineBanner title="t" dismissal="persistent" actions={[{ id: 'a', label: 'l' }]} />,
    );
    expect(screen.getByText('按数字键选择')).toBeInTheDocument();

    rerender(<InlineBanner title="t" dismissal="dismissible" actions={[{ id: 'a', label: 'l' }]} />);
    expect(screen.getByText('按数字键选择 · esc 关闭 · 输入可继续')).toBeInTheDocument();

    rerender(<InlineBanner title="t" dismissal="dismissible" />);
    expect(screen.getByText('esc 关闭 · 输入可继续')).toBeInTheDocument();
  });

  it('超过 8 行截断为 7 行加省略号', () => {
    const title = Array.from({ length: 10 }, (_, i) => `第${i + 1}行`).join('\n');
    render(<InlineBanner title={title} />);
    expect(screen.getByText('第7行')).toBeInTheDocument();
    expect(screen.queryByText('第8行')).toBeNull();
    expect(screen.getByText('…')).toBeInTheDocument();
  });
});
