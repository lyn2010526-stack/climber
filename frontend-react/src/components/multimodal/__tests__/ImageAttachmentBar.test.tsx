import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  formatBytes,
  isImageFile,
  nextAttachmentId,
  readAttachmentDataUrl,
  readingAttachment,
  screenImageFile,
  screenAttachmentFile,
  type ImageAttachment,
} from '../attachments';
import { ImageAttachmentBar } from '../ImageAttachmentBar';

function imageFile(name = 'cat.png', size = 1024, type = 'image/png'): File {
  return new File(['x'.repeat(size)], name, { type });
}

function makeAttachment(overrides: Partial<ImageAttachment> = {}): ImageAttachment {
  return {
    id: 'img-1',
    url: 'data:image/png;base64,QUJD',
    name: 'cat.png',
    size: 1024,
    status: 'ready',
    ...overrides,
  };
}

/** Stateful mount so the controlled API runs with a real useState setter. */
function Harness(props: {
  initial?: ImageAttachment[];
  onError?: (message: string) => void;
  disabled?: boolean;
}) {
  const [attachments, setAttachments] = useState<ImageAttachment[]>(props.initial ?? []);
  return (
    <ImageAttachmentBar
      attachments={attachments}
      onChange={setAttachments}
      onError={props.onError}
      disabled={props.disabled}
    />
  );
}

describe('attachment rules', () => {
  it('accepts image/* and rejects other MIME types', () => {
    expect(isImageFile(imageFile())).toBe(true);
    expect(isImageFile(new File(['x'], 'doc.pdf', { type: 'application/pdf' }))).toBe(false);
  });

  it('rejects oversize files with a size reason', () => {
    const result = screenImageFile(imageFile('big.png', 6 * 1024 * 1024), {
      currentCount: 0,
      maxImages: 4,
      maxSizeBytes: 5 * 1024 * 1024,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.rejection.reason).toBe('size');
  });

  it('enforces the per-message image limit', () => {
    const result = screenImageFile(imageFile(), { currentCount: 4, maxImages: 4, maxSizeBytes: 5 * 1024 * 1024 });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.rejection.reason).toBe('limit');
  });

  it('accepts supported document attachments and rejects executable types', () => {
    expect(screenAttachmentFile(new File(['pdf'], 'brief.pdf', { type: 'application/pdf' }), {
      currentCount: 0, maxImages: 4, maxSizeBytes: 100,
    }).ok).toBe(true);
    expect(screenAttachmentFile(new File(['x'], 'run.exe', { type: 'application/octet-stream' }), {
      currentCount: 0, maxImages: 4, maxSizeBytes: 100,
    }).ok).toBe(false);
  });

  it('formats sizes for display', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(2048)).toBe('2 KB');
    expect(formatBytes(3 * 1024 * 1024)).toBe('3.0 MB');
  });

  it('builds reading attachments and resolves data URLs', async () => {
    const file = imageFile('pasted.png', 10);
    const reading = readingAttachment(file);
    expect(reading.status).toBe('reading');
    expect(reading.url).toBe('');

    const resolved = await readAttachmentDataUrl(file);
    expect(resolved.status).toBe('ready');
    expect(resolved.url).toMatch(/^data:image\/png;base64,/);
  });

  it('generates unique ids', () => {
    expect(nextAttachmentId()).not.toBe(nextAttachmentId());
  });
});

describe('ImageAttachmentBar', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('adds a picked image and resolves the chip to a ready thumbnail', async () => {
    const user = userEvent.setup();
    const onError = vi.fn();
    render(<Harness onError={onError} />);

    await user.upload(
      screen.getByTestId('image-attachment-input'),
      imageFile('photo.jpg', 4, 'image/jpeg'),
    );

    await waitFor(() => {
      expect(screen.getByTestId('image-preview-thumb')).toHaveAttribute(
        'src',
        expect.stringMatching(/^data:image\/jpeg;base64,/),
      );
    });
    expect(screen.getByText('photo.jpg')).toBeInTheDocument();
    expect(onError).not.toHaveBeenCalled();
  });

  it('reports rejected files to onError and adds nothing', () => {
    const onChange = vi.fn();
    const onError = vi.fn();
    render(<ImageAttachmentBar attachments={[]} onChange={onChange} onError={onError} />);

    // Bypass the input accept filter so the MIME rule itself is exercised.
    // Documents (.txt/.pdf/.md/.csv) are supported attachments; an executable
    // never is.
    fireEvent.change(screen.getByTestId('image-attachment-input'), {
      target: { files: [new File(['x'], 'run.exe', { type: 'application/octet-stream' })] },
    });

    expect(onChange).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith('Unsupported attachment type.');
    expect(screen.queryByTestId('image-preview-chip')).not.toBeInTheDocument();
  });

  it('attaches pasted images from the document paste event', async () => {
    render(<Harness />);

    fireEvent.paste(document, { clipboardData: { files: [imageFile('pasted.png', 4)] } });

    await waitFor(() => {
      expect(screen.getByTestId('image-preview-thumb')).toBeInTheDocument();
    });
    expect(screen.getByText('pasted.png')).toBeInTheDocument();
  });

  it('renders ready chips with a remove button and drops the right one', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const attachments = [makeAttachment({ id: 'img-1' }), makeAttachment({ id: 'img-2', name: 'dog.png' })];
    render(<ImageAttachmentBar attachments={attachments} onChange={onChange} />);

    const chips = screen.getAllByTestId('image-preview-chip');
    expect(chips).toHaveLength(2);
    expect(screen.getAllByTestId('image-preview-thumb')).toHaveLength(2);

    await user.click(screen.getAllByTestId('image-preview-remove')[0]);
    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ id: 'img-2' })]);
  });

  it('disables attach at the image limit', () => {
    render(
      <ImageAttachmentBar
        attachments={Array.from({ length: 4 }, (_, index) => makeAttachment({ id: `img-${index}` }))}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('image-attach-button')).toBeDisabled();
    expect(screen.getAllByTestId('image-preview-remove')).toHaveLength(4);
  });

  it('disables attach and removal while disabled', () => {
    render(<ImageAttachmentBar attachments={[makeAttachment()]} onChange={vi.fn()} disabled />);
    expect(screen.getByTestId('image-attach-button')).toBeDisabled();
    expect(screen.getByTestId('image-preview-remove')).toBeDisabled();
  });

  it('shows the reading spinner instead of a thumbnail while reading', () => {
    render(<ImageAttachmentBar attachments={[makeAttachment({ status: 'reading', url: '' })]} onChange={vi.fn()} />);
    expect(screen.queryByTestId('image-preview-thumb')).not.toBeInTheDocument();
    expect(screen.getByText('Reading…')).toBeInTheDocument();
  });
});
