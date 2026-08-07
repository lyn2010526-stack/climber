import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../LoginPage';

describe('LoginPage', () => {
  it('renders login page without crashing', () => {
    const { container } = render(<MemoryRouter><LoginPage /></MemoryRouter>);
    expect(container).toBeDefined();
  });
});
