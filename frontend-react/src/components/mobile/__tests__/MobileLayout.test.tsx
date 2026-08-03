import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileLayout } from '../MobileLayout';

describe('MobileLayout', () => {
  it('renders header with Climber branding', () => {
    render(
      <MobileLayout currentPage="chat" onNavigate={() => {}}>
        <div>Content</div>
      </MobileLayout>
    );
    expect(screen.getByText('Climber')).toBeDefined();
  });

  it('renders children content', () => {
    render(
      <MobileLayout currentPage="chat" onNavigate={() => {}}>
        <div data-testid="child">Child Content</div>
      </MobileLayout>
    );
    expect(screen.getByTestId('child')).toBeDefined();
  });

  it('renders bottom navigation', () => {
    render(
      <MobileLayout currentPage="chat" onNavigate={() => {}}>
        <div>Content</div>
      </MobileLayout>
    );
    expect(screen.getByText('工作台')).toBeDefined();
  });
});
