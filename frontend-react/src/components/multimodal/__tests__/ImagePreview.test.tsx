import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ImagePreview } from '../ImagePreview';
import type { ImageAttachment } from '../attachments';

function attachment(overrides: Partial<ImageAttachment> = {}): ImageAttachment {
  return {
    id: 'img-1',
    url: 'data:image/png;base64,QUJD',
    name: 'cat.png',
    size: 2048,
    status: 'ready',
    ...overrides,
  };
}

describe('ImagePreview', () => {
  it('renders the thumbnail, name and formatted size when ready', () => {
    render(<ImagePreview attachment={attachment()} />);
    expect(screen.getByTestId('image-preview-thumb')).toHaveAttribute('src', 'data:image/png;base64,QUJD');
    expect(screen.getByAltText('cat.png')).toBeInTheDocument();
    expect(screen.getByText('2 KB')).toBeInTheDocument();
    expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready');
  });

  it('marks the reading state and hides the thumbnail until data arrives', () => {
    render(<ImagePreview attachment={attachment({ status: 'reading', url: '' })} />);
    expect(screen.queryByTestId('image-preview-thumb')).not.toBeInTheDocument();
    expect(screen.getByText('Reading…')).toBeInTheDocument();
    expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'reading');
  });

  it('shows a failure label in the error state', () => {
    render(<ImagePreview attachment={attachment({ status: 'error', error: 'size' })} />);
    expect(screen.getByText('Too large')).toBeInTheDocument();
    expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'error');
  });

  it('removes through onRemove with the attachment id', async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    render(<ImagePreview attachment={attachment({ id: 'img-7', name: 'dog.png' })} onRemove={onRemove} />);
    await user.click(screen.getByRole('button', { name: 'Remove dog.png' }));
    expect(onRemove).toHaveBeenCalledWith('img-7');
  });

  it('omits the remove button entirely without onRemove', () => {
    render(<ImagePreview attachment={attachment()} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
