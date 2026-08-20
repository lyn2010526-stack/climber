import { useState, useEffect } from 'react';
import { FolderTree } from 'lucide-react';
import { api } from '../../../api';

export function FilesPanel() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDocuments = async () => {
      setLoading(true);
      try {
        const data = await api.listDocuments();
          setDocuments(data || []);
      } catch { /* skip */ }
      setLoading(false);
    };
    fetchDocuments();
  }, []);

  if (loading) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">加载文档中...</p>
        <div className="space-y-1">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-6 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">项目文件浏览器</p>
        <div className="text-center py-8">
          <FolderTree size={24} className="mx-auto text-[var(--color-text-muted)]" />
           <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无上传文档</p>
           <p className="text-[10px] text-[var(--color-text-muted)] mt-1">上传文档后可用于知识检索</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
       <p className="text-xs text-[var(--color-text-muted)]">已上传文档 ({documents.length})</p>
      <div className="bg-white/5 rounded-2xl p-1.5 space-y-0.5 border border-white/10">
        {documents.map(doc => (
          <div key={doc.id} className="flex items-center gap-2 py-1.5 px-2 rounded-xl hover:bg-white/5 text-xs text-[var(--color-text-secondary)] transition-colors">
            <FolderTree size={12} className="text-[var(--color-text-muted)]" />
            <span className="truncate flex-1">{doc.filename || doc.name}</span>
             {doc.chunks && <span className="text-[10px] text-[var(--color-text-muted)]">{doc.chunks} 段</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
