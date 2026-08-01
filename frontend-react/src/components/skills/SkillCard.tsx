import React from 'react';
import { cn } from '../../lib/utils';

interface SkillCardProps {
  skill: {
    id: string;
    name: string;
    description: string;
    category: string;
    enabled: boolean;
    installCount?: number;
    rating?: number;
    icon?: React.ReactNode;
    tags?: string[];
  };
  onToggle: (id: string) => void;
  onSelect?: (id: string) => void;
  selected?: boolean;
}

const categoryGradients: Record<string, string> = {
  productivity: 'from-blue-500 to-cyan-400',
  development: 'from-violet-500 to-purple-400',
  communication: 'from-pink-500 to-rose-400',
  analysis: 'from-amber-500 to-orange-400',
  creative: 'from-emerald-500 to-teal-400',
  utility: 'from-slate-500 to-gray-400',
};

const categoryBg: Record<string, string> = {
  productivity: 'bg-blue-500/10 text-blue-400',
  development: 'bg-violet-500/10 text-violet-400',
  communication: 'bg-pink-500/10 text-pink-400',
  analysis: 'bg-amber-500/10 text-amber-400',
  creative: 'bg-emerald-500/10 text-emerald-400',
  utility: 'bg-slate-500/10 text-slate-400',
};

export function SkillCard({ skill, onToggle, onSelect, selected }: SkillCardProps) {
  const gradient = categoryGradients[skill.category] || categoryGradients.utility;
  const badgeClass = categoryBg[skill.category] || categoryBg.utility;

  return (
    <div
      onClick={() => onSelect?.(skill.id)}
      className={cn(
        'group relative rounded-2xl border transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer',
        'hover:translate-y-[-2px] hover:shadow-xl hover:shadow-black/30',
        selected
          ? 'border-blue-500/40 bg-blue-500/[0.06] shadow-lg shadow-blue-500/10'
          : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]'
      )}
    >
      {/* Active indicator */}
      {skill.enabled && (
        <div className="absolute top-3 right-3">
          <div className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
          </div>
        </div>
      )}

      <div className="p-5">
        {/* Icon */}
        <div className={cn(
          'w-11 h-11 rounded-xl bg-gradient-to-br flex items-center justify-center mb-4 shadow-lg',
          gradient
        )}>
          {skill.icon || (
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          )}
        </div>

        {/* Name & Category */}
        <h3 className="text-sm font-semibold text-white mb-1 truncate">{skill.name}</h3>
        <p className="text-xs text-gray-500 leading-relaxed line-clamp-2 mb-3">{skill.description}</p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          <span className={cn('px-2 py-0.5 rounded-lg text-[10px] font-medium', badgeClass)}>
            {skill.category}
          </span>
          {skill.tags?.slice(0, 2).map(tag => (
            <span key={tag} className="px-2 py-0.5 rounded-lg text-[10px] font-medium bg-white/[0.04] text-gray-500 border border-white/[0.06]">
              {tag}
            </span>
          ))}
        </div>

        {/* Stats & Action */}
        <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
          <div className="flex items-center gap-3 text-[10px] text-gray-500">
            {skill.installCount != null && (
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {skill.installCount >= 1000
                  ? `${(skill.installCount / 1000).toFixed(1)}k`
                  : skill.installCount}
              </span>
            )}
            {skill.rating != null && (
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                {skill.rating.toFixed(1)}
              </span>
            )}
          </div>

          <button
            onClick={(e) => { e.stopPropagation(); onToggle(skill.id); }}
            className={cn(
              'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200',
              skill.enabled
                ? 'bg-white/[0.06] text-gray-400 hover:bg-red-500/10 hover:text-red-400'
                : 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20'
            )}
          >
            {skill.enabled ? '禁用' : '安装'}
          </button>
        </div>
      </div>
    </div>
  );
}
