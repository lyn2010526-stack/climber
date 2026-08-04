import { useState, useCallback, forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import { Upload, File, X, CheckCircle, AlertCircle, FileText, Image, Film, Music, Archive } from 'lucide-react';
import { cn } from '../../lib/utils';

const uploadZoneVariants = cva(
  'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer',
  {
    variants: {
      variant: {
        default: 'border-white/[0.1] bg-white/[0.02] hover:border-blue-500/40 hover:bg-blue-500/[0.03]',
        active: 'border-blue-500/60 bg-blue-500/[0.05] shadow-lg shadow-blue-500/10',
        error: 'border-red-500/40 bg-red-500/[0.03]',
        success: 'border-emerald-500/40 bg-emerald-500/[0.03]',
      },
      size: {
        sm: 'p-4 min-h-[80px]',
        md: 'p-6 min-h-[120px]',
        lg: 'p-8 min-h-[160px]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

const fileItemVariants = cva(
  'flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-all duration-200',
  {
    variants: {
      status: {
        pending: 'border-white/[0.06] bg-white/[0.02]',
        uploading: 'border-blue-500/20 bg-blue-500/[0.03]',
        success: 'border-emerald-500/20 bg-emerald-500/[0.03]',
        error: 'border-red-500/20 bg-red-500/[0.03]',
      },
    },
    defaultVariants: {
      status: 'pending',
    },
  }
);

interface FileUploadProps {
  onFilesSelected?: (files: File[]) => void;
  onFileRemove?: (id: string) => void;
  accept?: Record<string, string[]>;
  maxSize?: number;
  maxFiles?: number;
  multiple?: boolean;
  disabled?: boolean;
  files?: UploadFile[];
  className?: string;
  variant?: 'default' | 'active' | 'error' | 'success';
  size?: 'sm' | 'md' | 'lg';
}

interface UploadFile {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  preview?: string;
}

function getFileIcon(file: File) {
  const type = file.type;
  if (type.startsWith('image/')) return <Image className="h-4 w-4 text-violet-400" />;
  if (type.startsWith('video/')) return <Film className="h-4 w-4 text-pink-400" />;
  if (type.startsWith('audio/')) return <Music className="h-4 w-4 text-amber-400" />;
  if (type.includes('zip') || type.includes('rar') || type.includes('tar') || type.includes('gz')) {
    return <Archive className="h-4 w-4 text-orange-400" />;
  }
  if (type.includes('pdf') || type.includes('document') || type.includes('text')) {
    return <FileText className="h-4 w-4 text-blue-400" />;
  };
  return <File className="h-4 w-4 text-white/50" />;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

const FileUpload = forwardRef<HTMLDivElement, FileUploadProps>(
  ({ onFilesSelected, onFileRemove, accept, maxSize = 10 * 1024 * 1024, maxFiles = 10, multiple = true, disabled, files: controlledFiles, className, variant, size = 'md', ...props }, ref) => {
    const [isDragging, setIsDragging] = useState(false);
    const [internalFiles, setInternalFiles] = useState<UploadFile[]>([]);
    const files = controlledFiles || internalFiles;

    const processFiles = useCallback((fileList: FileList | File[]) => {
      const newFiles: UploadFile[] = Array.from(fileList).slice(0, maxFiles).map((file) => {
        const uploadFile: UploadFile = {
          id: generateId(),
          file,
          progress: 0,
          status: 'pending',
        };

        if (maxSize && file.size > maxSize) {
          uploadFile.status = 'error';
          uploadFile.error = `文件大小超过 ${formatFileSize(maxSize)} 限制`;
        }

        if (file.type.startsWith('image/')) {
          uploadFile.preview = URL.createObjectURL(file);
        }

        return uploadFile;
      });

      setInternalFiles((prev) => [...prev, ...newFiles]);
      onFilesSelected?.(newFiles.map((f) => f.file));
    }, [maxFiles, maxSize, onFilesSelected]);

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

    const handleRemove = useCallback((id: string) => {
      const file = files.find((f) => f.id === id);
      if (file?.preview) URL.revokeObjectURL(file.preview);
      setInternalFiles((prev) => prev.filter((f) => f.id !== id));
      onFileRemove?.(id);
    }, [files, onFileRemove]);

    const currentVariant = disabled ? 'default' : isDragging ? 'active' : variant || 'default';

    return (
      <div ref={ref} className={cn('w-full space-y-3', className)} {...props}>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && document.getElementById('file-upload-input')?.click()}
          className={cn(uploadZoneVariants({ variant: currentVariant, size }), disabled && 'opacity-50 cursor-not-allowed')}
        >
          <input
            id="file-upload-input"
            type="file"
            className="hidden"
            accept={accept ? Object.keys(accept).join(',') : undefined}
            multiple={multiple}
            disabled={disabled}
            onChange={handleInputChange}
          />
          <Upload className={cn('mb-2 text-white/30', size === 'sm' && 'h-5 w-5', size === 'md' && 'h-7 w-7', size === 'lg' && 'h-9 w-9')} />
          <p className={cn('text-white/60', size === 'sm' && 'text-xs', size === 'md' && 'text-sm', size === 'lg' && 'text-base')}>
            {isDragging ? '释放以上传文件' : '拖拽文件到此处或点击上传'}
          </p>
          <p className={cn('text-white/30 mt-1', size === 'sm' && 'text-[10px]', size !== 'sm' && 'text-xs')}>
            支持 {Object.keys(accept || {}).join('、') || '所有文件类型'}
            {maxSize && `，单个文件不超过 ${formatFileSize(maxSize)}`}
          </p>
        </div>

        {files.length > 0 && (
          <div className="space-y-2">
            {files.map((file) => (
              <div key={file.id} className={cn(fileItemVariants({ status: file.status }))}>
                {file.preview ? (
                  <img src={file.preview} alt="" className="h-8 w-8 rounded object-cover shrink-0" />
                ) : (
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-white/[0.05] shrink-0">
                    {getFileIcon(file.file)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs text-white truncate">{file.file.name}</p>
                    <span className="text-[10px] text-white/40 shrink-0">{formatFileSize(file.file.size)}</span>
                  </div>
                  {file.status === 'uploading' && (
                    <div className="mt-1.5 h-1 w-full rounded-full bg-white/[0.06] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                  {file.error && (
                    <p className="mt-0.5 text-[10px] text-red-400 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {file.error}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {file.status === 'success' && <CheckCircle className="h-4 w-4 text-emerald-400" />}
                  {file.status === 'uploading' && (
                    <span className="text-[10px] text-blue-400">{file.progress}%</span>
                  )}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); handleRemove(file.id); }}
                    className="p-0.5 rounded hover:bg-white/10 text-white/30 hover:text-white/60 transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
);
FileUpload.displayName = 'FileUpload';

export { FileUpload, uploadZoneVariants, fileItemVariants, formatFileSize };
export type { FileUploadProps, UploadFile };
