import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RichTextEditor } from '../RichTextEditor';

describe('RichTextEditor', () => {
  it('renders editor with placeholder attribute', () => {
    render(<RichTextEditor placeholder="请输入内容" />);
    const editor = screen.getByRole('textbox');
    expect(editor.getAttribute('data-placeholder')).toBe('请输入内容');
  });

  it('renders toolbar with formatting buttons', () => {
    render(<RichTextEditor />);
    expect(screen.getByLabelText('粗体')).toBeDefined();
    expect(screen.getByLabelText('斜体')).toBeDefined();
    expect(screen.getByLabelText('下划线')).toBeDefined();
  });

  it('calls onChange when content changes', () => {
    const handleChange = vi.fn();
    render(<RichTextEditor onChange={handleChange} />);
    const editor = screen.getByRole('textbox');
    fireEvent.input(editor, { target: { innerHTML: '<p>Hello</p>' } });
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders with different sizes', () => {
    const { container } = render(<RichTextEditor size="lg" />);
    expect(container.querySelector('.min-h-\\[200px\\]')).not.toBeNull();
  });

  it('renders character count when maxLength is set', () => {
    render(<RichTextEditor maxLength={100} />);
    expect(screen.getByText('0 / 100')).toBeDefined();
  });

  it('disables editing when disabled prop is true', () => {
    render(<RichTextEditor disabled />);
    const editor = screen.getByRole('textbox');
    expect(editor.getAttribute('contenteditable')).toBe('false');
  });

  it('renders heading buttons', () => {
    render(<RichTextEditor />);
    expect(screen.getByLabelText('标题1')).toBeDefined();
    expect(screen.getByLabelText('标题2')).toBeDefined();
    expect(screen.getByLabelText('标题3')).toBeDefined();
    expect(screen.getByLabelText('段落')).toBeDefined();
  });

  it('renders list buttons', () => {
    render(<RichTextEditor />);
    expect(screen.getByLabelText('无序列表')).toBeDefined();
    expect(screen.getByLabelText('有序列表')).toBeDefined();
    expect(screen.getByLabelText('引用')).toBeDefined();
  });

  it('renders alignment buttons', () => {
    render(<RichTextEditor />);
    expect(screen.getByLabelText('左对齐')).toBeDefined();
    expect(screen.getByLabelText('居中')).toBeDefined();
    expect(screen.getByLabelText('右对齐')).toBeDefined();
  });
});
