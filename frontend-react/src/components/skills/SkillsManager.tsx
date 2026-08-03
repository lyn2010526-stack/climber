import React, { useState, useMemo } from 'react';
import {
  Search, Filter, Grid3X3, List, Plus, RefreshCw,
  ChevronRight, Sparkles, X,
} from 'lucide-react';
import { SkillCard } from './SkillCard';
import { cn } from '../../lib/utils';

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  installCount?: number;
  rating?: number;
  tags?: string[];
}

const categories = ['全部', 'productivity', 'development', 'communication', 'analysis', 'creative', 'utility'];

const mockSkills: Skill[] = [
  { id: '1', name: 'Code Formatter', description: '自动格式化多种语言的代码，支持 Prettier、Black、gofmt', category: 'development', enabled: true, installCount: 12400, rating: 4.8, tags: ['format', 'lint'] },
  { id: '2', name: 'Email Composer', description: '智能撰写和回复邮件，支持多语言', category: 'communication', enabled: false, installCount: 8300, rating: 4.6, tags: ['email', 'writing'] },
  { id: '3', name: 'Data Analyzer', description: '分析数据集并生成可视化报告', category: 'analysis', enabled: true, installCount: 5600, rating: 4.7, tags: ['data', 'chart'] },
  { id: '4', name: 'Task Planner', description: '将复杂任务分解为可执行的子任务', category: 'productivity', enabled: false, installCount: 15200, rating: 4.9, tags: ['plan', 'todo'] },
  { id: '5', name: 'Image Generator', description: '基于描述生成高质量图像', category: 'creative', enabled: false, installCount: 9800, rating: 4.5, tags: ['image', 'ai'] },
  { id: '6', name: 'API Tester', description: '测试 REST 和 GraphQL 接口', category: 'development', enabled: true, installCount: 4200, rating: 4.4, tags: ['api', 'test'] },
  { id: '7', name: 'Meeting Notes', description: '自动整理会议记录和行动项', category: 'productivity', enabled: false, installCount: 6700, rating: 4.3, tags: ['meeting', 'notes'] },
  { id: '8', name: 'SQL Optimizer', description: '分析和优化 SQL 查询性能', category: 'development', enabled: false, installCount: 3100, rating: 4.6, tags: ['sql', 'db'] },
];

export function SkillsManager() {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('全部');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skills, setSkills] = useState(mockSkills);

  const filtered = useMemo(() => {
    return skills.filter(skill => {
      const matchSearch = !search ||
        skill.name.toLowerCase().includes(search.toLowerCase()) ||
        skill.description.toLowerCase().includes(search.toLowerCase()) ||
        skill.tags?.some(t => t.toLowerCase().includes(search.toLowerCase()));
      const matchCategory = activeCategory === '全部' || skill.category === activeCategory;
      return matchSearch && matchCategory;
    });
  }, [skills, search, activeCategory]);

  const toggleSkill = (id: string) => {
    setSkills(prev => prev.map(s =>
      s.id === id ? { ...s, enabled: !s.enabled } : s
    ));
  };

  const selectedSkill = skills.find(s => s.id === selectedId);

  return (
    <div className="flex h-full">
      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 pt-6 pb-4">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 shadow-lg shadow-blue-500/20">
                <Sparkles size={18} className="text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">技能管理</h1>
                 <p className="text-xs text-[var(--color-text-muted)] mt-0.5">已启用 {skills.filter(s => s.enabled).length} / {skills.length} 个技能</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.08] transition-all">
                <RefreshCw size={14} />
              </button>
              <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 text-white text-xs font-medium shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover:brightness-110 transition-all">
                <Plus size={13} />
                安装技能
              </button>
            </div>
          </div>

           {/* Search & Filters */}
           <div className="flex items-center gap-3">
             <div className="flex-1 relative">
               <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
               <input
                 type="text"
                 value={search}
                 onChange={e => setSearch(e.target.value)}
                 placeholder="搜索技能..."
                  className="w-full h-9 pl-9 pr-4 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-[var(--color-text-secondary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/40 focus:bg-white/[0.06] transition-all"
               />
               {search && (
                 <button
                   onClick={() => setSearch('')}
                   className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                 >
                   <X size={13} />
                 </button>
               )}
             </div>

             {/* View toggle */}
             <div className="flex items-center bg-white/[0.04] rounded-xl border border-white/[0.06] p-0.5">
               <button
                 onClick={() => setViewMode('grid')}
                 className={cn(
                   'p-1.5 rounded-lg transition-all',
                   viewMode === 'grid' ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                 )}
               >
                 <Grid3X3 size={14} />
               </button>
               <button
                 onClick={() => setViewMode('list')}
                 className={cn(
                   'p-1.5 rounded-lg transition-all',
                   viewMode === 'list' ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                 )}
               >
                 <List size={14} />
               </button>
             </div>
           </div>

          {/* Category pills */}
          <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-1 scrollbar-none">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all',
                  activeCategory === cat
                    ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                    : 'bg-white/[0.03] text-[var(--color-text-muted)] border border-white/[0.06] hover:text-[var(--color-text-secondary)] hover:bg-white/[0.06]'
                )}
              >
                {cat === '全部' ? cat : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Skills grid */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Filter size={32} className="text-[var(--color-text-muted)] mb-3" />
              <p className="text-sm text-[var(--color-text-muted)]">没有找到匹配的技能</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">尝试其他搜索词或分类</p>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {filtered.map(skill => (
                <SkillCard
                  key={skill.id}
                  skill={skill}
                  onToggle={toggleSkill}
                  onSelect={setSelectedId}
                  selected={selectedId === skill.id}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map(skill => (
                <ListItem key={skill.id} skill={skill} onToggle={toggleSkill} onSelect={setSelectedId} selected={selectedId === skill.id} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selectedSkill && (
        <SkillDetail skill={selectedSkill} onToggle={toggleSkill} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}

function ListItem({ skill, onToggle, onSelect, selected }: Omit<React.ComponentProps<typeof SkillCard>, 'className'>) {
  return (
    <div
      onClick={() => onSelect?.(skill.id)}
      className={cn(
        'flex items-center gap-4 px-4 py-3 rounded-xl border cursor-pointer transition-all duration-200',
        selected
          ? 'border-blue-500/30 bg-blue-500/[0.06]'
          : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/[0.1]'
      )}
    >
      <div className={cn(
        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
        skill.enabled ? 'bg-green-500/10 text-green-400' : 'bg-white/[0.04] text-[var(--color-text-muted)]'
      )}>
        <Sparkles size={14} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate">{skill.name}</span>
          <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-white/[0.04] text-[var(--color-text-muted)]">{skill.category}</span>
        </div>
        <p className="text-xs text-[var(--color-text-muted)] truncate mt-0.5">{skill.description}</p>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onToggle(skill.id); }}
        className={cn(
          'px-3 py-1 rounded-lg text-[11px] font-medium transition-all flex-shrink-0',
          skill.enabled
            ? 'bg-white/[0.06] text-[var(--color-text-secondary)] hover:bg-red-500/10 hover:text-red-400'
            : 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20'
        )}
      >
        {skill.enabled ? '禁用' : '安装'}
      </button>
      <ChevronRight size={14} className="text-[var(--color-text-muted)] flex-shrink-0" />
    </div>
  );
}

function SkillDetail({ skill, onToggle, onClose }: { skill: Skill; onToggle: (id: string) => void; onClose: () => void }) {
  return (
    <div className="w-80 border-l border-white/[0.06] bg-[#0D0D12]/80 backdrop-blur-xl flex flex-col">
      <div className="p-5 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">技能详情</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.06] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">
            <X size={14} />
          </button>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center shadow-lg">
            <Sparkles size={18} className="text-white" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">{skill.name}</h4>
            <p className="text-[11px] text-[var(--color-text-muted)] capitalize">{skill.category}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        <div>
          <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">描述</label>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">{skill.description}</p>
        </div>

        <div>
          <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">标签</label>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {skill.tags?.map(tag => (
              <span key={tag} className="px-2 py-0.5 rounded-lg text-[10px] bg-white/[0.04] text-[var(--color-text-secondary)] border border-white/[0.06]">
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1">安装量</div>
            <div className="text-sm font-semibold text-white">{skill.installCount?.toLocaleString()}</div>
          </div>
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1">评分</div>
            <div className="text-sm font-semibold text-white flex items-center gap-1">
              <span className="text-amber-400">{skill.rating}</span>
              <span className="text-[10px] text-[var(--color-text-muted)]">/ 5.0</span>
            </div>
          </div>
        </div>

        <div>
          <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">状态</label>
          <div className="mt-1.5 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${skill.enabled ? 'bg-green-500' : 'bg-[var(--color-text-muted)]'}`} />
            <span className="text-xs text-[var(--color-text-secondary)]">{skill.enabled ? '已启用' : '已禁用'}</span>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-white/[0.06]">
        <button
          onClick={() => onToggle(skill.id)}
          className={cn(
            'w-full py-2.5 rounded-xl text-xs font-medium transition-all',
            skill.enabled
              ? 'bg-red-500/10 text-red-400 hover:bg-red-500/15 border border-red-500/20'
              : 'bg-gradient-to-r from-blue-500 to-violet-500 text-white shadow-lg shadow-blue-500/20 hover:brightness-110'
          )}
        >
          {skill.enabled ? '禁用此技能' : '安装并启用'}
        </button>
      </div>
    </div>
  );
}
