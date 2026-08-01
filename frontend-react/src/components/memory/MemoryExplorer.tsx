import React, { useState, useMemo } from 'react';
import {
  Search, Folder, FileText, Plus, ChevronRight,
  ChevronDown, Edit3, GitHistory, X,
  FolderOpen,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface MemoryFile {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder';
  content?: string;
  lastModified?: string;
  size?: number;
  children?: MemoryFile[];
}

const mockTree: MemoryFile[] = [
  {
    id: '1',
    name: 'project',
    path: '/project',
    type: 'folder',
    children: [
      { id: '1-1', name: 'architecture.md', path: '/project/architecture.md', type: 'file', content: '# 系统架构\n\n基于微服务架构设计...', lastModified: '2024-01-15', size: 2048 },
      { id: '1-2', name: 'decisions.md', path: '/project/decisions.md', type: 'file', content: '# 架构决策记录\n\n## ADR-001: 使用 Rust', lastModified: '2024-01-14', size: 1536 },
      {
        id: '1-3', name: 'api', path: '/project/api', type: 'folder',
        children: [
          { id: '1-3-1', name: 'endpoints.md', path: '/project/api/endpoints.md', type: 'file', content: '# API 端点清单', lastModified: '2024-01-13', size: 890 },
          { id: '1-3-2', name: 'auth.md', path: '/project/api/auth.md', type: 'file', content: '# 认证方案', lastModified: '2024-01-12', size: 670 },
        ],
      },
    ],
  },
  {
    id: '2', name: 'context', path: '/context', type: 'folder',
    children: [
      { id: '2-1', name: 'user-preferences.md', path: '/context/user-preferences.md', type: 'file', content: '# 用户偏好\n\n- 语言: 中文', lastModified: '2024-01-16', size: 340 },
      { id: '2-2', name: 'session-notes.md', path: '/context/session-notes.md', type: 'file', content: '# 会话笔记', lastModified: '2024-01-16', size: 1200 },
    ],
  },
  { id: '3', name: 'MEMORY.md', path: '/MEMORY.md', type: 'file', content: '# 用户指令记忆\n\n本文件记录了用户的指令和偏好。', lastModified: '2024-01-16', size: 512 },
];

export function MemoryExplorer() {
  const [selectedFile, setSelectedFile] = useState<MemoryFile | null>(null);
  const [search, setSearch] = useState('');
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['1', '1-3', '2']));

  const toggleFolder = (id: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const flattenAndFilter = (nodes: MemoryFile[], query: string): MemoryFile[] => {
    const result: MemoryFile[] = [];
    for (const node of nodes) {
      if (node.type === 'folder' && node.children) {
        const filteredChildren = flattenAndFilter(node.children, query);
        if (filteredChildren.length > 0 || node.name.toLowerCase().includes(query.toLowerCase())) {
          result.push({ ...node, children: filteredChildren });
        }
      } else if (node.name.toLowerCase().includes(query.toLowerCase()) || node.content?.toLowerCase().includes(query.toLowerCase())) {
        result.push(node);
      }
    }
    return result;
  };

  const displayTree = useMemo(() => {
    if (!search) return mockTree;
    return flattenAndFilter(mockTree, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  return (
    <div className="flex h-full">
      {/* File tree */}
      <div className="w-72 border-r border-white/[0.06] flex flex-col">
        <div className="px-4 pt-5 pb-3">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">记忆文件</h3>
            <button className="p-1.5 rounded-lg bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all">
              <Plus size={13} />
            </button>
          </div>
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜索记忆..."
              className="w-full h-8 pl-8 pr-3 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {displayTree.map(node => (
            <TreeNode
              key={node.id}
              node={node}
              depth={0}
              expandedFolders={expandedFolders}
              onToggle={toggleFolder}
              onSelect={setSelectedFile}
              selectedId={selectedFile?.id}
            />
          ))}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedFile && selectedFile.type === 'file' ? (
          <FileContent file={selectedFile} onClose={() => setSelectedFile(null)} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center">
            <FolderOpen size={40} className="text-gray-700 mb-3" />
            <p className="text-sm text-gray-500">选择一个文件查看内容</p>
            <p className="text-xs text-gray-600 mt-1">从左侧文件树中点击文件</p>
          </div>
        )}
      </div>
    </div>
  );
}

function TreeNode({
  node, depth, expandedFolders, onToggle, onSelect, selectedId,
}: {
  node: MemoryFile;
  depth: number;
  expandedFolders: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (node: MemoryFile) => void;
  selectedId?: string;
}) {
  const isExpanded = expandedFolders.has(node.id);
  const isSelected = selectedId === node.id;
  const paddingLeft = depth * 16 + 8;

  return (
    <div>
      <button
        onClick={() => node.type === 'folder' ? onToggle(node.id) : onSelect(node)}
        className={cn(
          'w-full flex items-center gap-1.5 py-1.5 pr-2 rounded-lg text-left transition-colors',
          isSelected ? 'bg-blue-500/10 text-blue-400' : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-200'
        )}
        style={{ paddingLeft: `${paddingLeft}px` }}
      >
        {node.type === 'folder' ? (
          <>
            {isExpanded ? <ChevronDown size={12} className="flex-shrink-0" /> : <ChevronRight size={12} className="flex-shrink-0" />}
            <Folder size={13} className={cn('flex-shrink-0', isExpanded ? 'text-blue-400' : 'text-gray-500')} />
          </>
        ) : (
          <>
            <span className="w-3 flex-shrink-0" />
            <FileText size={13} className="flex-shrink-0 text-gray-500" />
          </>
        )}
        <span className="text-xs truncate">{node.name}</span>
      </button>
      {node.type === 'folder' && isExpanded && node.children?.map(child => (
        <TreeNode
          key={child.id}
          node={child}
          depth={depth + 1}
          expandedFolders={expandedFolders}
          onToggle={onToggle}
          onSelect={onSelect}
          selectedId={selectedId}
        />
      ))}
    </div>
  );
}

function FileContent({ file, onClose }: { file: MemoryFile; onClose: () => void }) {
  const [isEditing, setIsEditing] = useState(false);
  const [content, setContent] = useState(file.content || '');

  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <FileText size={14} className="text-blue-400" />
          <span className="text-sm font-medium text-white">{file.name}</span>
          <span className="text-[10px] text-gray-600">{file.lastModified}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button className="p-1.5 rounded-lg bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all" title="Git 历史">
            <GitHistory size={13} />
          </button>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={cn(
              'p-1.5 rounded-lg transition-all',
              isEditing ? 'bg-blue-500/10 text-blue-400' : 'bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08]'
            )}
            title="编辑"
          >
            <Edit3 size={13} />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {isEditing ? (
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            className="w-full h-full bg-transparent text-sm text-gray-200 font-mono leading-relaxed resize-none focus:outline-none"
          />
        ) : (
          <pre className="text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
            {content}
          </pre>
        )}
      </div>

      {/* Status bar */}
      <div className="px-5 py-2 border-t border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-4 text-[10px] text-gray-600">
          <span>{content.length} 字符</span>
          <span>{content.split(/\s+/).filter(Boolean).length} 词</span>
          <span>{content.split('\n').length} 行</span>
        </div>
        {isEditing && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setIsEditing(false); setContent(file.content || ''); }}
              className="px-3 py-1 rounded-lg text-[11px] text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all"
            >
              取消
            </button>
            <button className="px-3 py-1 rounded-lg text-[11px] bg-blue-500/10 text-blue-400 hover:bg-blue-500/15 transition-all font-medium">
              保存
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
