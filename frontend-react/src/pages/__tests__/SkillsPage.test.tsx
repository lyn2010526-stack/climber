import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SkillsPage } from '../SkillsPage';

vi.mock('../../api', () => ({
  api: {
    listSkills: vi.fn().mockResolvedValue({ skills: [] }),
    toggleSkill: vi.fn().mockResolvedValue({}),
  },
}));

describe('SkillsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(<SkillsPage />);
    expect(container).toBeDefined();
  });

  it('renders page structure', () => {
    const { container } = render(<SkillsPage />);
    expect(container.querySelector('.h-full')).not.toBeNull();
  });
});
