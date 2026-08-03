import { useCallback, useState, type ReactNode } from 'react';
import { useDropzone } from 'react-dropzone';

interface DropZoneProps {
  onFilesDrop: (files: File[]) => void;
  children: ReactNode;
}

export function DropZone({ onFilesDrop, children }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setIsDragging(false);
      if (acceptedFiles.length > 0) {
        onFilesDrop(acceptedFiles);
      }
    },
    [onFilesDrop]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': [],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/*': [],
    },
    noClick: true,
    onDragEnter: () => setIsDragging(true),
    onDragLeave: () => setIsDragging(false),
    onDropAccepted: () => setIsDragging(false),
    onDropRejected: () => setIsDragging(false),
  });

  return (
    <div
      {...getRootProps()}
      className="relative flex-1 flex flex-col"
    >
      <input {...getInputProps()} />
      {children}
      {(isDragActive || isDragging) && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-blue-600/5 ring-2 ring-blue-500/50 rounded-xl pointer-events-none transition-all">
          <div className="text-center">
            <div className="text-blue-400 mb-2">
              <svg
                className="w-12 h-12 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
             <p className="text-[var(--color-text-primary)] font-medium text-sm">拖拽文件到此处</p>
             <p className="text-[var(--color-text-muted)] text-xs mt-1">支持图片、PDF、DOCX 或文本文件</p>
          </div>
        </div>
      )}
    </div>
  );
}
