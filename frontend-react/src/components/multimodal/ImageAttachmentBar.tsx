import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { ImagePlus, Loader2 } from 'lucide-react';

import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import {
  ATTACHMENT_INPUT_ACCEPT,
  MAX_CHAT_IMAGES,
  MAX_IMAGE_SIZE_BYTES,
  readAttachmentDataUrl,
  readingAttachment,
  screenAttachmentFile,
  type ImageAttachment,
} from './attachments';
import { ImagePreview } from './ImagePreview';

/**
 * Attachment bar for chat input: image/file picker, clipboard paste, thumbnail
 * chips and per-item removal. Self-contained; a chat composer mounts it and
 * forwards `attachments` with its send call (`api.chatStream` attachments).
 */

/** Accepts a whole list or an updater so a `useState` setter satisfies it. */
export type AttachmentsChange = (
  next: ImageAttachment[] | ((prev: ImageAttachment[]) => ImageAttachment[]),
) => void;

export interface ImageAttachmentBarProps {
  /** Controlled attachment list. */
  attachments: ImageAttachment[];
  /** Replaces the list after adds/removals; updater form is supported. */
  onChange: AttachmentsChange;
  /** Surfaced for user-facing validation feedback (type/size/limit). */
  onError?: (message: string) => void;
  maxImages?: number;
  maxSizeBytes?: number;
  disabled?: boolean;
  /** Accept attribute for the file input. */
  accept?: string;
  /** Listen for image pastes on the document; turn off when the composer handles paste itself. */
  pasteEnabled?: boolean;
  className?: string;
}

export function ImageAttachmentBar({
  attachments,
  onChange,
  onError,
  maxImages = MAX_CHAT_IMAGES,
  maxSizeBytes = MAX_IMAGE_SIZE_BYTES,
  disabled = false,
  accept = ATTACHMENT_INPUT_ACCEPT,
  pasteEnabled = true,
  className,
}: ImageAttachmentBarProps) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const [busy, setBusy] = useState(false);
  const readingRef = useRef(0);

  const addFiles = useCallback(
    async (files: Iterable<File>) => {
      const incoming = Array.from(files);
      if (incoming.length === 0) return;

      const accepted: Array<{ file: File; attachment: ImageAttachment }> = [];
      let count = attachments.length;
      for (const file of incoming) {
        const screened = screenAttachmentFile(file, {
          currentCount: count,
          maxImages,
          maxSizeBytes,
          accept,
        });
        if (!screened.ok) {
          onError?.(screened.rejection.message);
          continue;
        }
        count += 1;
        accepted.push({ file, attachment: readingAttachment(file) });
      }
      if (accepted.length === 0) return;

      onChange((prev) => [...prev, ...accepted.map((entry) => entry.attachment)]);
      setBusy(true);
      readingRef.current += accepted.length;
      await Promise.all(
        accepted.map(async ({ file, attachment }) => {
          const resolved = await readAttachmentDataUrl(file);
          readingRef.current -= 1;
          if (readingRef.current === 0) setBusy(false);
          onChange((prev) =>
            prev.map((item) => (item.id === attachment.id ? { ...item, ...resolved } : item)),
          );
        }),
      );
    },
    [accept, attachments, maxImages, maxSizeBytes, onChange, onError],
  );

  const removeAttachment = useCallback(
    (id: string) => onChange(attachments.filter((attachment) => attachment.id !== id)),
    [attachments, onChange],
  );

  useEffect(() => {
    if (disabled || !pasteEnabled) return;
    const onPaste = (event: ClipboardEvent) => {
      const files = Array.from(event.clipboardData?.files ?? []);
      if (files.length === 0) return;
      event.preventDefault();
      void addFiles(files);
    };
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, [addFiles, disabled, pasteEnabled]);

  return (
    <div className={cn('flex flex-wrap items-center gap-1.5', className)} data-testid="image-attachment-bar">
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={accept}
        multiple
        className="sr-only"
        onChange={(event) => {
          void addFiles(event.target.files ?? []);
          event.target.value = '';
        }}
        data-testid="image-attachment-input"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || busy || attachments.length >= maxImages}
         aria-label="Attach files"
        aria-controls={inputId}
        className={cn(
          'flex h-7 items-center gap-1 rounded-full px-2 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]',
          'transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]',
          'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
          'disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none',
        )}
        data-testid="image-attach-button"
      >
        {busy
          ? <Loader2 aria-hidden className="size-3.5 animate-spin" />
          : <ImagePlus aria-hidden className="size-3.5" />}
         <span>{t('chat.attach')}</span>
      </button>
      {attachments.map((attachment) => (
        <ImagePreview
          key={attachment.id}
          attachment={attachment}
          onRemove={removeAttachment}
          disabled={disabled}
        />
      ))}
    </div>
  );
}
