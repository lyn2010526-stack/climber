import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FormField } from '../Field';

describe('FormField', () => {
  it('renders label', () => {
    render(<FormField label="Username">content</FormField>);
    expect(screen.getByText('Username')).toBeDefined();
  });

  it('renders children', () => {
    render(<FormField><span>Field Content</span></FormField>);
    expect(screen.getByText('Field Content')).toBeDefined();
  });

  it('renders description', () => {
    render(<FormField description="This is a hint">content</FormField>);
    expect(screen.getByText('This is a hint')).toBeDefined();
  });

  it('renders error message', () => {
    render(<FormField error="Something went wrong">content</FormField>);
    expect(screen.getByText('Something went wrong')).toBeDefined();
  });

  it('renders hint when no error', () => {
    render(<FormField hint="Helper text">content</FormField>);
    expect(screen.getByText('Helper text')).toBeDefined();
  });

  it('marks label as required', () => {
    const { container } = render(<FormField label="Email" required>content</FormField>);
    expect(container.querySelector('label span')?.textContent).toBe('*');
  });

  it('links label to htmlFor', () => {
    const { container } = render(<FormField label="Email" htmlFor="email">content</FormField>);
    expect(container.querySelector('label')?.getAttribute('for')).toBe('email');
  });

  it('applies custom className', () => {
    const { container } = render(<FormField className="field-custom">content</FormField>);
    expect(container.querySelector('.field-custom')).not.toBeNull();
  });

  it('does not render hint when error exists', () => {
    render(<FormField error="Error" hint="Helper">content</FormField>);
    expect(screen.queryByText('Helper')).toBeNull();
    expect(screen.getByText('Error')).toBeDefined();
  });
});
