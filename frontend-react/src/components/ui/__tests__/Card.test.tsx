import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardDescription, CardFooter } from '../Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeDefined();
  });

  it('renders header and title', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
        </CardHeader>
      </Card>
    );
    expect(screen.getByText('Title')).toBeDefined();
    expect(screen.getByText('Description')).toBeDefined();
  });

  it('renders footer', () => {
    render(
      <Card>
        <CardFooter>Footer action</CardFooter>
      </Card>
    );
    expect(screen.getByText('Footer action')).toBeDefined();
  });

  it('applies bordered variant', () => {
    const { container } = render(<Card variant="bordered">Bordered</Card>);
    expect(container.querySelector('.border-white\\/10')).not.toBeNull();
  });
});
