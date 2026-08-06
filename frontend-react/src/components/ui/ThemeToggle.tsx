import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme.tsx';
import { cn } from '../../lib/utils';

export const ThemeToggle: React.FC<{ className?: string }> = ({ className }) => {
  const { theme, toggleTheme, isLoading } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      disabled={isLoading}
      className={cn(
        'p-2 rounded-xl transition-all duration-200 border border-transparent',
        'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'active:scale-95',
        className
      )}
      title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
      aria-label={`当前为${theme === 'dark' ? '深色' : '浅色'}模式，点击切换`}
    >
      <div className="relative w-4 h-4">
        <Sun 
          size={16} 
          className={cn(
            "transition-all duration-300",
            theme === 'dark' ? 'opacity-0 rotate-90 scale-75 absolute' : 'opacity-100 rotate-0 scale-100 relative'
          )} 
        />
        <Moon 
          size={16} 
          className={cn(
            "transition-all duration-300",
            theme === 'light' ? 'opacity-0 -rotate-90 scale-75 absolute' : 'opacity-100 rotate-0 scale-100 relative'
          )} 
        />
      </div>
    </button>
  );
};

export default ThemeToggle;
