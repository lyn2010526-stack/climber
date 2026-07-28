import { useState } from 'react';
import {
  Database, Plus, Trash2, Edit3, Clock, Link2, Search,
  Star, Archive,
} from 'lucide-react';

interface MemoryEntry {
  id: string;
  content: string;
  type: 'fact' | 'decision' | 'constraint' | 'architecture';
  weight: number; // 1-10
  projectBinding: string;
  tags: string[];
  createdAt: number;
  expiresAt: number | null;
}

const defaultEntry: Omit<MemoryEntry, 'id' | 'createdAt'> = {
  content: '',
  type: 'fact',
  weight: 5,
  projectBinding: '',
  tags: [],
  expiresAt: null,
};

export function MemoryKnowledgeBase() {
  const [entries, setEntries] = useState<MemoryEntry[]>([
    {
      id: '1',
      content: 'Project uses FastAPI + React with async-first architecture',
      type: 'architecture',
      weight: 9,
      projectBinding: '/workspace/agent-engine',
      tags: ['architecture', 'tech-stack'],
      createdAt: Date.now() - 86400000,
      expiresAt: null,
    },
    {
      id: '2',
      content: 'All database queries must use parameterized queries to prevent SQL injection',
      type: 'constraint',
      weight: 10,
      projectBinding: '/workspace/agent-engine',
      tags: ['security', 'database'],
      createdAt: Date.now() - 172800000,
      expiresAt: null,
    },
    {
      id: '3',
      content: 'Chose Chroma over Pinecone for vector DB due to no external service requirement',
      type: 'decision',
      weight: 7,
      projectBinding: '/workspace/agent-engine',
      tags: ['decision', 'vector-db'],
      createdAt: Date.now() - 259200000,
      expiresAt: Date.now() + 604800000,
    },
  ]);

  const [editingEntry, setEditingEntry] = useState<Partial<MemoryEntry> | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('');

  const filtered = entries.filter(e => {
    const matchSearch = !searchQuery || e.content.toLowerCase().includes(searchQuery.toLowerCase());
    const matchType = !filterType || e.type === filterType;
    return matchSearch && matchType;
  });

  const saveEntry = () => {
    if (!editingEntry?.content) return;
    if (editingEntry.id) {
      setEntries(prev => prev.map(e => e.id === editingEntry.id ? { ...e, ...editingEntry } as MemoryEntry : e));
    } else {
      const newEntry: MemoryEntry = {
        ...defaultEntry,
        ...editingEntry,
        id: `mem-${Date.now()}`,
        createdAt: Date.now(),
      } as MemoryEntry;
      setEntries(prev => [newEntry, ...prev]);
    }
    setEditingEntry(null);
  };

  const typeColors: Record<string, string> = {
    fact: 'bg-blue-600/10 text-blue-400',
    decision: 'bg-purple-500/10 text-purple-400',
    constraint: 'bg-amber-500/10 text-amber-400',
    architecture: 'bg-green-500/10 text-green-400',
  };

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Database size={16} className="text-blue-400" />
           <h3 className="text-sm font-semibold">持久记忆</h3>
        </div>
        <button
          onClick={() => setEditingEntry({ ...defaultEntry })}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={12} /> Add Entry
        </button>
      </div>

      {/* Search & Filter */}
      <div className="px-4 py-2 border-b border-gray-700 flex gap-2">
        <div className="flex-1 relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
             placeholder="搜索记忆..."
            className="w-full pl-7 pr-3 py-1.5 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-2 py-1.5 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100"
        >
           <option value="">全部类型</option>
           <option value="fact">事实</option>
           <option value="decision">决策</option>
           <option value="constraint">约束</option>
           <option value="architecture">架构</option>
        </select>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {editingEntry && (
          <div className="p-3 bg-gray-800 border border-blue-500/30 rounded-xl mb-3">
            <textarea
              value={editingEntry.content || ''}
              onChange={(e) => setEditingEntry({ ...editingEntry, content: e.target.value })}
              className="w-full h-20 px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100 resize-none focus:outline-none focus:border-blue-500/50"
               placeholder="记忆内容..."
            />
            <div className="grid grid-cols-2 gap-2 mt-2">
              <select
                value={editingEntry.type || 'fact'}
                onChange={(e) => setEditingEntry({ ...editingEntry, type: e.target.value as any })}
                className="px-2 py-1.5 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100"
              >
                 <option value="fact">事实</option>
                 <option value="decision">决策</option>
                 <option value="constraint">约束</option>
                 <option value="architecture">架构</option>
              </select>
              <input
                type="number"
                min={1}
                max={10}
                value={editingEntry.weight || 5}
                onChange={(e) => setEditingEntry({ ...editingEntry, weight: parseInt(e.target.value) })}
                className="px-2 py-1.5 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-100"
                 placeholder="权重 1-10"
              />
            </div>
            <div className="flex gap-2 mt-2">
              <button
                onClick={saveEntry}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded-lg"
              >
                 {editingEntry.id ? '更新' : '保存'}
              </button>
              <button
                onClick={() => setEditingEntry(null)}
                className="px-3 py-1 text-xs text-gray-400 bg-gray-700 rounded-lg"
              >
                 取消
              </button>
            </div>
          </div>
        )}

        {filtered.map(entry => (
          <div key={entry.id} className="p-3 bg-gray-800 border border-gray-700 rounded-xl hover:border-blue-500/20 transition-colors">
            <div className="flex items-start gap-2">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0 ${typeColors[entry.type]}`}>
                {entry.type}
              </span>
              <p className="text-xs text-gray-100 flex-1">{entry.content}</p>
            </div>
            <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
              <span className="flex items-center gap-0.5">
                <Star size={9} /> {entry.weight}/10
              </span>
              {entry.projectBinding && (
                <span className="flex items-center gap-0.5">
                  <Link2 size={9} /> {entry.projectBinding}
                </span>
              )}
              <span className="flex items-center gap-0.5">
                <Clock size={9} /> {new Date(entry.createdAt).toLocaleDateString()}
              </span>
              <div className="flex-1" />
              <button
                onClick={() => setEditingEntry(entry)}
                className="p-0.5 hover:text-blue-400"
              >
                <Edit3 size={10} />
              </button>
              <button
                onClick={() => setEntries(prev => prev.filter(e => e.id !== entry.id))}
                className="p-0.5 hover:text-red-400"
              >
                <Trash2 size={10} />
              </button>
            </div>
            {entry.tags.length > 0 && (
              <div className="flex gap-1 mt-1.5">
                {entry.tags.map(tag => (
                  <span key={tag} className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-500">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Archive size={24} className="mx-auto mb-2 opacity-30" />
            <p className="text-xs">No memory entries found</p>
          </div>
        )}
      </div>
    </div>
  );
}
