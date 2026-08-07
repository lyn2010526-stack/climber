import React, { useState, useRef, useCallback, useId } from 'react';
import { cn } from '../../lib/utils';
import { Upload, X, File, Image, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

export interface FileUploadProps {
  accept?: string;
  multiple?: boolean;
  maxSize?: number;
  maxFiles?: number;
  disabled?: boolean;
  onChange?: (files: File[]) => void;
  onError?: (error: string) => void;
  label?: string;
  hint?: string;
  className?: string;
  preview?: boolean;
}

interface FileItem {
  file: File;
  id: string;
  progress: number;
  error?: string;
  preview?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
  accept,
  multiple = false,
  maxSize = 10 * 1024 * 1024,
  maxFiles = 10,
  disabled = false,
  onChange,
  onError,
  label,
  hint,
  className,
  preview = true,
}) => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const generatedId = useId();

  const validateFile = useCallback((file: File): string | undefined => {
    if (file.size > maxSize) {
      return `File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`;
    }
    if (accept) {
      const acceptedTypes = accept.split(',').map(t => t.trim());
      const isAccepted = acceptedTypes.some(type => {
        if (type.startsWith('.')) return file.name.toLowerCase().endsWith(type.toLowerCase());
        if (type.includes('*')) return file.type.startsWith(type.replace('/*', '/'));
        return file.type === type;
      });
      if (!isAccepted) return 'File type not accepted';
    }
    return undefined;
  }, [accept, maxSize]);

  const processFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    if (!multiple && fileArray.length > 1) {
      onError?.('Only one file allowed');
      return;
    }
    if (files.length + fileArray.length > maxFiles) {
      onError?.(`Maximum ${maxFiles} files allowed`);
      return;
    }

    const processed: FileItem[] = fileArray.map(file => {
      const error = validateFile(file);
      const item: FileItem = {
        file,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        progress: error ? 0 : 0,
        error,
      };

      if (preview && file.type.startsWith('image/') && !error) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setFiles(prev => prev.map(f => f.id === item.id ? { ...f, preview: e.target?.result as string } : f));
        };
        reader.readAsDataURL(file);
      }

      return item;
    });

    setFiles(prev => multiple ? [...prev, ...processed] : processed);
    onChange?.(multiple ? [...files.map(f => f.file), ...fileArray] : fileArray);
  }, [files, maxFiles, multiple, onChange, onError, preview, validateFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    if (e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  }, [disabled, processFiles]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
      e.target.value = '';
    }
  }, [processFiles]);

  const removeFile = useCallback((id: string) => {
    setFiles(prev => {
      const updated = prev.filter(f => f.id !== id);
      onChange?.(updated.map(f => f.file));
      return updated;
    });
  }, [onChange]);

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <Image className="w-[var(--icon-md)] h-[var(--icon-md)] text-[var(--color-info)]" />;
    if (type.includes('pdf') || type.includes('text')) return <FileText className="w-[var(--icon-md)] h-[var(--icon-md)] text-[var(--color-danger)]" />;
    return <File className="w-[var(--icon-md)] h-[var(--icon-md)] text-[var(--text-muted)]" />;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className={cn('flex flex-col gap-[var(--space-1-5)] w-full', className)}>
      {label && (
        <label className="text-[var(--font-size-sm)] font-medium text-[var(--text-primary)]">{label}</label>
      )}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={cn(
          'relative flex flex-col items-center justify-center gap-[var(--space-2)] p-[var(--space-6)] border-2 border-dashed rounded-[var(--radius-xl)] transition-all duration-[var(--transition-normal)] cursor-pointer',
          isDragging ? 'border-[var(--accent)] bg-[var(--accent-subtle)]' : 'border-[var(--border-default)] bg-[var(--surface-bg-subtle)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-bg-hover)]',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        role="button"
        aria-label="Upload files"
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click(); } }}
      >
        <div className={cn(
          'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
          isDragging ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface-bg)] text-[var(--text-muted)]'
        )}>
          <Upload className="w-[var(--icon-xl)] h-[var(--icon-xl)]" />
        </div>
        <div className="text-center">
          <p className="text-[var(--font-size-sm)] text-[var(--text-primary)]">
            <span className="text-[var(--accent)] font-medium">Click to upload</span> or drag and drop
          </p>
          {hint && <p className="text-[var(--font-size-xs)] text-[var(--text-muted)] mt-[var(--space-0-5)]">{hint}</p>}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled}
          aria-hidden="true"
        />
      </div>

      {files.length > 0 && (
        <div className="flex flex-col gap-[var(--space-2)]">
          {files.map(item => (
            <div
              key={item.id}
              className={cn(
                'flex items-center gap-[var(--space-3)] p-[var(--space-3)] rounded-[var(--radius-lg)] border transition-colors',
                item.error ? 'border-[var(--color-danger-border)] bg-[var(--color-danger-subtle)]' : 'border-[var(--border-subtle)] bg-[var(--surface-bg)]'
              )}
            >
              {item.preview ? (
                <img src={item.preview} alt={item.file.name} className="w-10 h-10 rounded-[var(--radius-md)] object-cover shrink-0" />
              ) : (
                <div className="shrink-0">{getFileIcon(item.file.type)}</div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-[var(--font-size-sm)] text-[var(--text-primary)] truncate">{item.file.name}</p>
                <p className="text-[var(--font-size-xs)] text-[var(--text-muted)]">{formatSize(item.file.size)}</p>
                {item.error && (
                  <p className="text-[var(--font-size-xs)] text-[var(--color-danger)] flex items-center gap-[var(--space-1)] mt-[var(--space-0-5)]">
                    <AlertCircle className="w-3 h-3" />
                    {item.error}
                  </p>
                )}
              </div>
              {!item.error && item.progress === 100 && (
                <CheckCircle2 className="w-[var(--icon-md)] h-[var(--icon-md)] text-[var(--color-success)] shrink-0" />
              )}
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(item.id); }}
                className="p-[var(--space-1)] rounded-[var(--radius-md)] text-[var(--text-muted)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-subtle)] transition-colors shrink-0"
                aria-label={`Remove ${item.file.name}`}
              >
                <X className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export { FileUpload };
