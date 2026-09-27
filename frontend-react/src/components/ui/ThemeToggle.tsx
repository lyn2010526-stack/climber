import React from 'react';
import { icons, iconSizes } from '../../lib/icons';
import { useTheme } from '../../hooks/useTheme.tsx';
import { cn } from '../../lib/utils';

export const ThemeToggle: React.FC<{ className?: string }> = ({ className }) => {
  const { theme, toggleTheme, isLoading } = useTheme();
  // The glyph names the mode the control reports, so the dark theme shows the
  // moon. Both come from the shared icon table, never a local glyph.
  const ThemeIcon = theme === 'dark' ? icons.darkTheme : icons.lightTheme;

  return (
    <button type="button"
      onClick={toggleTheme}
      disabled={isLoading}
      data-state={theme}
      className={cn(
        // 44x44 is the touch-target baseline. The icon alone would size this to
        // 34x34, which is why the padding sits inside a min-size floor instead
        // of being the only thing making the control big enough.
        'flex min-h-11 min-w-11 items-center justify-center rounded-[var(--radius-lg)] border border-transparent transition-colors duration-150 motion-reduce:transition-none',
        // Three states all resolve to the accent, because all three mean the
        // control is live: at rest it names the mode in the secondary rung,
        // hover and press bring it to the accent foreground, and focus takes
        // the shared ring, which is accent over a page-coloured gap.
        'text-[var(--color-text-secondary)]',
        'hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-accent-foreground)]',
        'active:bg-[var(--color-accent-subtle)] active:text-[var(--color-accent-foreground)]',
        'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
        'disabled:cursor-not-allowed disabled:text-[var(--color-text-disabled)]',
        className
      )}
      title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
      aria-label={`当前为${theme === 'dark' ? '深色' : '浅色'}模式，点击切换`}
    >
      <ThemeIcon size={iconSizes.md} aria-hidden="true" focusable="false" />
    </button>
  );
};

export default ThemeToggle;
