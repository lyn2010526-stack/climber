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
        'p-2 rounded-xl transition-colors duration-150 border border-transparent',
        'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
      aria-label={`当前为${theme === 'dark' ? '深色' : '浅色'}模式，点击切换`}
    >
      <div className="relative w-4 h-4">
        <Sun 
          size={16} 
          className={cn(
            'transition-opacity duration-150',
            theme === 'dark' ? 'opacity-0 absolute' : 'opacity-100 relative'
          )} 
        />
        <Moon 
          size={16} 
          className={cn(
            'transition-opacity duration-150',
            theme === 'light' ? 'opacity-0 absolute' : 'opacity-100 relative'
          )} 
        />
      </div>
    </button>
  );
};

export default ThemeToggle;
