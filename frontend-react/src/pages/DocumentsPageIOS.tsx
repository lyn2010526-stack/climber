import { useState } from 'react';
import { FileText, File, Code, Plus } from 'lucide-react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSearchBar,
  IOSFab,
  IOSBadge,
  toast,
} from '../components/ios';
import { cn } from '../lib/utils';

type Category = 'all' | 'code' | 'doc' | 'config' | 'log';

interface Document {
  name: string;
  size: string;
  modified: string;
  category: 'code' | 'doc' | 'config' | 'log';
}

const documents: Document[] = [
  { name: 'README.md', size: '12.4 KB', modified: '2026-08-05 14:30', category: 'doc' },
  { name: 'app.tsx', size: '8.2 KB', modified: '2026-08-05 10:15', category: 'code' },
  { name: 'config.yaml', size: '2.1 KB', modified: '2026-08-04 18:00', category: 'config' },
  { name: 'deploy.sh', size: '1.5 KB', modified: '2026-08-04 09:45', category: 'code' },
  { name: 'system.log', size: '256 KB', modified: '2026-08-06 08:20', category: 'log' },
  { name: 'schema.sql', size: '4.7 KB', modified: '2026-08-03 16:30', category: 'config' },
];

const categoryIcons: Record<string, typeof FileText> = {
  doc: FileText,
  code: Code,
  config: File,
  log: FileText,
};

export function DocumentsPageIOS() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<Category>('all');

  const categories: { value: Category; label: string }[] = [
    { value: 'all', label: '全部' },
    { value: 'code', label: '代码' },
    { value: 'doc', label: '文档' },
    { value: 'config', label: '配置' },
    { value: 'log', label: '日志' },
  ];

  const filteredDocs = documents.filter((d) => {
    const matchSearch = d.name.toLowerCase().includes(search.toLowerCase());
    const matchCategory = category === 'all' || d.category === category;
    return matchSearch && matchCategory;
  });

  return (
    <IOSPage className="h-full overflow-y-auto pb-24">
      <div className="px-4 pt-6 pb-2">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">文档管理</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          浏览和管理所有项目文件
        </p>
      </div>

      <div className="px-4 py-3">
        <div className="ios-segmented flex gap-1 p-1 rounded-lg bg-[var(--color-bg-surface-2)]">
          {categories.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setCategory(cat.value)}
              className={cn(
                'ios-segment flex-1 py-1.5 text-sm rounded-md transition-colors',
                category === cat.value && 'active'
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 pb-3">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索文档..."
        />
      </div>

      <IOSListGroup title="文件列表" className="mb-6">
        {filteredDocs.map((doc) => {
          const Icon = categoryIcons[doc.category] || File;
          return (
            <IOSListItem
              key={doc.name}
              icon={<Icon size={18} className="text-white" />}
              iconBg="var(--color-accent)"
              title={
                <span className="flex flex-col">
                  <span>{doc.name}</span>
                  <span className="ios-footnote text-[var(--color-text-muted)] font-normal">
                    {doc.size}
                  </span>
                </span>
              }
              detail={
                <span className="text-[var(--color-text-muted)] ios-footnote">
                  {doc.modified}
                </span>
              }
              onClick={() => toast.info(`打开 ${doc.name}`)}
            />
          );
        })}
      </IOSListGroup>

      <IOSListGroup title="存储统计" className="mb-6">
        <IOSListItem
          icon={<File size={18} className="text-white" />}
          iconBg="#007AFF"
          title="总文件数"
          detail={<span className="text-[var(--color-text-muted)]">128</span>}
          showChevron={false}
        />
        <IOSListItem
          icon={<FileText size={18} className="text-white" />}
          iconBg="#34C759"
          title="已用空间"
          detail={<span className="text-[var(--color-text-muted)]">45.2 MB</span>}
          showChevron={false}
        />
        <IOSListItem
          icon={<File size={18} className="text-white" />}
          iconBg="#FF9500"
          title="剩余空间"
          detail={<span className="text-[var(--color-text-muted)]">54.8 MB</span>}
          showChevron={false}
        />
      </IOSListGroup>

      <IOSFab
        icon={<Plus size={20} />}
        label="上传文档"
        onClick={() => toast.info('打开文件上传对话框')}
      />
    </IOSPage>
  );
}

export default DocumentsPageIOS;
