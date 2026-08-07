import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeToggle } from '../ThemeToggle';
import { ThemeProvider } from '../../../hooks/useTheme.tsx';

describe('ThemeToggle', () => {
  it('renders toggle button', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );
    expect(screen.getByRole('button')).toBeDefined();
  });

  it('handles click without crashing', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );
    screen.getByRole('button').click();
    expect(screen.getByRole('button')).toBeDefined();
  });

  it('applies custom className', () => {
    render(
      <ThemeProvider>
        <ThemeToggle className="custom-toggle" />
      </ThemeProvider>
    );
    expect(screen.getByRole('button').className).toContain('custom-toggle');
  });
});
