import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MessagesPage } from '../MessagesPage';

describe('MessagesPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );
    expect(screen.getByText('消息记录')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('搜索消息...')).toBeDefined();
  });

  it('renders mock messages', () => {
    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Python 数据处理脚本')).toBeDefined();
  });
});
