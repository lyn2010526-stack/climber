import { useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSCard,
  IOSConfirmDialog,
  toast,
} from '../components/ios';
import {
  Home,
  ChevronRight,
  Folder,
  FileText,
  Code,
  Image as ImageIcon,
  Download,
  Pencil,
  Trash2,
  HardDrive,
} from 'lucide-react';
import { cn } from '../lib/utils';

type FileKind = 'folder' | 'code' | 'text' | 'image';

interface FileEntry {
  id: number;
  name: string;
  kind: FileKind;
  meta: string;
  modified: string;
}

const FILES: FileEntry[] = [
  { id: 1, name: '项目文档', kind: 'folder', meta: '12 项', modified: '2026-08-05 14:30' },
  { id: 2, name: '数据分析', kind: 'folder', meta: '8 项', modified: '2026-08-04 09:45' },
  { id: 3, name: 'deploy.sh', kind: 'code', meta: '8.2 KB', modified: '2026-08-06 10:12' },
  { id: 4, name: '需求规格说明.pdf', kind: 'text', meta: '2.4 MB', modified: '2026-08-03 16:20' },
  { id: 5, name: '架构图.png', kind: 'image', meta: '1.1 MB', modified: '2026-08-02 11:05' },
  { id: 6, name: '配置模板.yaml', kind: 'code', meta: '3.6 KB', modified: '2026-08-01 18:40' },
];

const KIND_ICON: Record<FileKind, typeof FileText> = {
  folder: Folder,
  code: Code,
  text: FileText,
  image: ImageIcon,
};

const KIND_COLOR: Record<FileKind, string> = {
  folder: '#FFB800',
  code: '#007AFF',
  text: '#8E8E93',
  image: '#AF52DE',
};

const USED_GB = 46.8;
const TOTAL_GB = 100;

export default function FilesPageIOS() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const selectedFile = FILES.find((file) => file.id === selectedId) ?? null;

  const handleDownload = () => {
    if (!selectedFile) return;
    toast.success(`开始下载「${selectedFile.name}」`);
  };

  const handleRename = () => {
    if (!selectedFile) return;
    toast.info(`重命名「${selectedFile.name}」功能开发中`);
  };

  const handleDelete = () => {
    if (!selectedFile) return;
    toast.success(`已删除「${selectedFile.name}」`);
    setSelectedId(null);
    setDeleteOpen(false);
  };

  return (
    <IOSPage className="pb-32">
      <div className="px-4 pt-6 space-y-5">
        <div>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">文件管理</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
            浏览与管理工作区文件
          </p>
        </div>

        <IOSCard className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-1.5 ios-caption text-[var(--color-text-muted)]">
              <HardDrive size={14} />
              存储占用
            </span>
            <span className="ios-caption text-[var(--color-text-primary)] font-medium">
              {USED_GB} GB / {TOTAL_GB} GB
            </span>
          </div>
          <div className="h-2 rounded-full bg-[var(--color-bg-surface-3)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--color-accent)]"
              style={{ width: `${(USED_GB / TOTAL_GB) * 100}%` }}
            />
          </div>
        </IOSCard>

        <IOSCard>
          <div className="flex items-center gap-1.5 px-4 py-3 overflow-x-auto whitespace-nowrap">
            <Home size={15} className="text-[var(--color-accent)] shrink-0" />
            <span className="ios-caption font-medium text-[var(--color-text-muted)]">工作区</span>
            <ChevronRight size={14} className="text-[var(--color-text-muted)] shrink-0" />
            <span className="ios-caption font-medium text-[var(--color-text-muted)]">data</span>
            <ChevronRight size={14} className="text-[var(--color-text-muted)] shrink-0" />
            <span className="ios-caption text-[var(--color-text-primary)]">项目</span>
          </div>
        </IOSCard>

        <IOSListGroup title="文件列表">
          {FILES.map((file) => {
            const Icon = KIND_ICON[file.kind];
            const selected = selectedId === file.id;
            return (
              <IOSListItem
                key={file.id}
                icon={<Icon size={18} className="text-white" />}
                iconBg={KIND_COLOR[file.kind]}
                title={file.name}
                showChevron={false}
                className={cn(
                  selected && '!bg-[var(--color-accent-subtle)] ring-2 ring-inset ring-[var(--color-accent)]'
                )}
                detail={
                  <span className="flex flex-col items-end gap-0.5">
                    <span className="ios-caption text-[var(--color-text-muted)]">{file.meta}</span>
                    <span className="ios-footnote text-[var(--color-text-muted)]">{file.modified}</span>
                    {selected && (
                      <span className="ios-footnote text-[var(--color-accent)] font-medium">已选中</span>
                    )}
                  </span>
                }
                onClick={() => setSelectedId(selected ? null : file.id)}
              />
            );
          })}
        </IOSListGroup>
      </div>

      <div className="fixed bottom-0 left-0 right-0 z-30 px-4 pt-3 pb-4 bg-[var(--color-bg-page)]/90 backdrop-blur-lg border-t border-[var(--color-border-subtle)]">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <button
            type="button"
            disabled={!selectedFile}
            onClick={handleDownload}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 py-2.5 rounded-[10px] ios-body font-medium transition-opacity',
              'bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] active:opacity-70',
              !selectedFile && 'opacity-40 pointer-events-none'
            )}
          >
            <Download size={16} />
            下载
          </button>
          <button
            type="button"
            disabled={!selectedFile}
            onClick={handleRename}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 py-2.5 rounded-[10px] ios-body font-medium transition-opacity',
              'bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] active:opacity-70',
              !selectedFile && 'opacity-40 pointer-events-none'
            )}
          >
            <Pencil size={16} />
            重命名
          </button>
          <button
            type="button"
            disabled={!selectedFile}
            onClick={() => setDeleteOpen(true)}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 py-2.5 rounded-[10px] ios-body font-medium transition-opacity',
              'bg-[var(--color-error-subtle)] text-[var(--color-error)] active:opacity-70',
              !selectedFile && 'opacity-40 pointer-events-none'
            )}
          >
            <Trash2 size={16} />
            删除
          </button>
        </div>
      </div>

      <IOSConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="删除文件"
        description={selectedFile ? `确定要删除「${selectedFile.name}」吗？此操作不可撤销。` : ''}
        onConfirm={handleDelete}
        confirmText="删除"
        danger
      />
    </IOSPage>
  );
}
