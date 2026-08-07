import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PageHeader } from '../PageHeader';

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="Test Page" />);
    expect(screen.getByText('Test Page')).toBeDefined();
  });

  it('renders description', () => {
    render(<PageHeader title="Test" description="Page description" />);
    expect(screen.getByText('Page description')).toBeDefined();
  });

  it('renders icon', () => {
    render(<PageHeader title="Test" icon={<span data-testid="icon">Icon</span>} />);
    expect(screen.getByTestId('icon')).toBeDefined();
  });

  it('renders actions', () => {
    render(<PageHeader title="Test" actions={<button>Action</button>} />);
    expect(screen.getByText('Action')).toBeDefined();
  });

  it('renders breadcrumbs', () => {
    render(
      <PageHeader
        title="Test"
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Current' }]}
      />
    );
    expect(screen.getByText('Home')).toBeDefined();
    expect(screen.getByText('Current')).toBeDefined();
  });

  it('renders without optional props', () => {
    render(<PageHeader title="Minimal" />);
    expect(screen.getByText('Minimal')).toBeDefined();
  });
});
