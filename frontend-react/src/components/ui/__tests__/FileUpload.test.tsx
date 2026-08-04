import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FileUpload, formatFileSize } from '../FileUpload';

describe('FileUpload', () => {
  it('renders upload zone with text', () => {
    render(<FileUpload />);
    expect(screen.getByText('拖拽文件到此处或点击上传')).toBeDefined();
  });

  it('renders with different sizes', () => {
    const { container } = render(<FileUpload size="lg" />);
    expect(container.querySelector('.p-8')).not.toBeNull();
  });

  it('calls onFilesSelected when files are selected via input', () => {
    const handleFiles = vi.fn();
    render(<FileUpload onFilesSelected={handleFiles} />);

    const file = new File(['test'], 'test.txt', { type: 'text/plain' });

    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    Object.defineProperty(input, 'files', {
      value: [file],
      configurable: true,
    });
    fireEvent.change(input);
    expect(handleFiles).toHaveBeenCalled();
  });

  it('renders file list when files are provided', () => {
    const files = [
      { id: '1', file: new File(['test'], 'test.txt', { type: 'text/plain' }), progress: 0, status: 'pending' as const },
    ];
    render(<FileUpload files={files} />);
    expect(screen.getByText('test.txt')).toBeDefined();
  });

  it('calls onFileRemove when remove button is clicked', () => {
    const handleRemove = vi.fn();
    const files = [
      { id: '1', file: new File(['test'], 'test.txt', { type: 'text/plain' }), progress: 0, status: 'pending' as const },
    ];
    render(<FileUpload files={files} onFileRemove={handleRemove} />);
    fireEvent.click(screen.getByRole('button', { hidden: true }));
    expect(handleRemove).toHaveBeenCalledWith('1');
  });

  it('shows progress for uploading files', () => {
    const files = [
      { id: '1', file: new File(['test'], 'test.txt', { type: 'text/plain' }), progress: 65, status: 'uploading' as const },
    ];
    render(<FileUpload files={files} />);
    expect(screen.getByText('65%')).toBeDefined();
  });

  it('shows error for files with error status', () => {
    const files = [
      { id: '1', file: new File(['test'], 'test.txt', { type: 'text/plain' }), progress: 0, status: 'error' as const, error: '文件过大' },
    ];
    render(<FileUpload files={files} />);
    expect(screen.getByText('文件过大')).toBeDefined();
  });

  it('disables interaction when disabled prop is true', () => {
    const { container } = render(<FileUpload disabled />);
    expect(container.querySelector('.opacity-50')).not.toBeNull();
  });
});

describe('formatFileSize', () => {
  it('formats bytes correctly', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1048576)).toBe('1 MB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });
});
