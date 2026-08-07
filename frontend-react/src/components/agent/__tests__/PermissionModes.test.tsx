import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PermissionModes, type PermissionMode } from '../PermissionModes';

describe('PermissionModes', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <PermissionModes currentMode="manual" onModeChange={() => {}} />
    );
    expect(container).toBeDefined();
  });

  it('renders all mode labels', () => {
    render(
      <PermissionModes currentMode="manual" onModeChange={() => {}} />
    );
    expect(screen.getByText('手动模式')).toBeDefined();
    expect(screen.getByText('计划模式')).toBeDefined();
    expect(screen.getByText('自动模式')).toBeDefined();
  });

  it('calls onModeChange when a mode is clicked', () => {
    const onModeChange = vi.fn();
    render(
      <PermissionModes currentMode="manual" onModeChange={onModeChange} />
    );
    fireEvent.click(screen.getByText('自动模式'));
    expect(onModeChange).toHaveBeenCalledWith('auto');
  });

  it('renders mode descriptions', () => {
    render(
      <PermissionModes currentMode="manual" onModeChange={() => {}} />
    );
    expect(screen.getByText('每个操作都需要你的确认')).toBeDefined();
    expect(screen.getByText('先预览再执行')).toBeDefined();
    expect(screen.getByText('全自动执行，仅高风险操作确认')).toBeDefined();
  });
});
