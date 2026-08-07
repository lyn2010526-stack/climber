import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DoctorPage } from '../DoctorPage';

vi.mock('../../api', () => ({
  api: {
    runDoctor: vi.fn().mockResolvedValue({ healthy: true, sections: [] }),
  },
}));

describe('DoctorPage', () => {
  it('renders page title', () => {
    render(<DoctorPage />);
    expect(screen.getByText('系统诊断')).toBeDefined();
  });

  it('renders description', () => {
    render(<DoctorPage />);
    expect(screen.getByText(/运行环境健康检查/)).toBeDefined();
  });

  it('renders refresh button', () => {
    render(<DoctorPage />);
    expect(screen.getByText('重新诊断')).toBeDefined();
  });
});
