/**
 * Shared model and validation for chat image attachments (multimodal contract).
 *
 * An attachment travels to the backend as its `url`: a base64 data URL for
 * locally picked/pasted files, or an http(s) URL. The backend accepts at most
 * `MAX_CHAT_IMAGES` references per chat message (see app/models/vision.py).
 */

export interface ImageAttachment {
  id: string;
  /** Preview and payload source: data URL once read, empty while reading. */
  url: string;
  name: string;
  size: number;
  status: 'reading' | 'ready' | 'error';
  /** Set when status is 'error'. */
  error?: 'type' | 'size' | 'limit' | 'read';
  kind?: 'image' | 'file';
  mimeType?: string;
}

/** Mirrors the backend contract in app/models/vision.py. */
export const MAX_CHAT_IMAGES = 4;
export const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;
export const IMAGE_INPUT_ACCEPT = 'image/*';
export const ATTACHMENT_INPUT_ACCEPT = 'image/*,.pdf,.txt,.md,.csv';

let attachmentSeq = 0;

export function nextAttachmentId(): string {
  attachmentSeq += 1;
  return `img-${Date.now().toString(36)}-${attachmentSeq}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isImageFile(file: File, accept = IMAGE_INPUT_ACCEPT): boolean {
  if (accept.endsWith('/*')) {
    return file.type.startsWith(accept.slice(0, -1));
  }
  return accept.split(',').some((candidate) => candidate.trim() === file.type);
}

export function isSupportedAttachment(file: File, accept = ATTACHMENT_INPUT_ACCEPT): boolean {
  return accept.split(',').some((candidate) => {
    const value = candidate.trim();
    return value.endsWith('/*') ? file.type.startsWith(value.slice(0, -1)) : value.startsWith('.') ? file.name.toLowerCase().endsWith(value) : file.type === value;
  });
}

/** Why a file was rejected; `message` is user-facing. */
export interface FileScreenRejection {
  reason: 'type' | 'size' | 'limit';
  message: string;
}

/**
 * Screen one file against the attachment limits. Pure so the rules stay
 * testable independent of the DOM.
 */
export function screenImageFile(
  file: File,
  limits: { currentCount: number; maxImages: number; maxSizeBytes: number; accept?: string },
): { ok: true } | { ok: false; rejection: FileScreenRejection } {
  if (!isImageFile(file, limits.accept)) {
    return { ok: false, rejection: { reason: 'type', message: 'Only image files are supported.' } };
  }
  if (file.size > limits.maxSizeBytes) {
    return {
      ok: false,
      rejection: {
        reason: 'size',
        message: `"${file.name}" is larger than ${formatBytes(limits.maxSizeBytes)}.`,
      },
    };
  }
  if (limits.currentCount >= limits.maxImages) {
    return {
      ok: false,
      rejection: {
        reason: 'limit',
        message: `At most ${limits.maxImages} images per message.`,
      },
    };
  }
  return { ok: true };
}

export function screenAttachmentFile(
  file: File,
  limits: { currentCount: number; maxImages: number; maxSizeBytes: number; accept?: string },
): { ok: true } | { ok: false; rejection: FileScreenRejection } {
  if (!isSupportedAttachment(file, limits.accept)) {
    return { ok: false, rejection: { reason: 'type', message: 'Unsupported attachment type.' } };
  }
  if (file.size > limits.maxSizeBytes) {
    return { ok: false, rejection: { reason: 'size', message: `"${file.name}" is larger than ${formatBytes(limits.maxSizeBytes)}.` } };
  }
  if (limits.currentCount >= limits.maxImages) {
    return { ok: false, rejection: { reason: 'limit', message: `At most ${limits.maxImages} attachments per message.` } };
  }
  return { ok: true };
}

/** Create a placeholder attachment in the reading state (no url yet). */
export function readingAttachment(file: File): ImageAttachment {
  return {
    id: nextAttachmentId(),
    url: '',
    name: file.name || 'pasted-image',
    size: file.size,
    status: 'reading',
    kind: file.type.startsWith('image/') ? 'image' : 'file',
    mimeType: file.type,
  };
}

/** Resolve the reading attachment into a ready data URL (or an error state). */
export function readAttachmentDataUrl(file: File): Promise<
  Pick<ImageAttachment, 'url' | 'status' | 'error'>
> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () =>
      resolve({ url: String(reader.result), status: 'ready', error: undefined });
    reader.onerror = () => resolve({ url: '', status: 'error', error: 'read' });
    reader.readAsDataURL(file);
  });
}
