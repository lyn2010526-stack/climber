import { useEffect, useState } from 'react';
import { FileText, X } from 'lucide-react';

interface AttachmentItem {
  id: string;
  file: File;
  previewUrl?: string;
}

interface AttachmentPreviewProps {
  files: AttachmentItem[];
  onRemove: (id: string) => void;
}

export function AttachmentPreview({ files, onRemove }: AttachmentPreviewProps) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4 py-2 border-t border-gray-700 bg-gray-800/30">
      {files.map((item) => (
        <AttachmentThumbnail key={item.id} item={item} onRemove={onRemove} />
      ))}
    </div>
  );
}

function AttachmentThumbnail({
  item,
  onRemove,
}: {
  item: AttachmentItem;
  onRemove: (id: string) => void;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const isImage = item.file.type.startsWith('image/');

  useEffect(() => {
    if (isImage) {
      const url = URL.createObjectURL(item.file);
      setObjectUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [item.file, isImage]);

  return (
    <div className="relative group">
      <div className="w-16 h-16 rounded-lg border border-gray-700 bg-gray-700 overflow-hidden flex items-center justify-center">
        {isImage && objectUrl ? (
          <img
            src={objectUrl}
            alt={item.file.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <FileText size={24} className="text-gray-500" />
        )}
      </div>
      <button
        onClick={() => onRemove(item.id)}
        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
        aria-label={`Remove ${item.file.name}`}
      >
        <X size={12} className="text-white" />
      </button>
      <p className="mt-1 max-w-[64px] text-[10px] text-gray-500 truncate text-center">
        {item.file.name}
      </p>
    </div>
  );
}
