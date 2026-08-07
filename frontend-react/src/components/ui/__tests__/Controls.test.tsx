import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Tabs, Toggle, Slider } from '../Controls';

describe('Tabs', () => {
  it('renders all tabs', () => {
    const tabs = [
      { id: 'tab1', label: 'Tab 1' },
      { id: 'tab2', label: 'Tab 2' },
    ];
    render(<Tabs tabs={tabs} activeTab="tab1" onChange={() => {}} />);
    expect(screen.getByText('Tab 1')).toBeDefined();
    expect(screen.getByText('Tab 2')).toBeDefined();
  });

  it('calls onChange when tab is clicked', () => {
    const onChange = vi.fn();
    const tabs = [{ id: 'tab1', label: 'Tab 1' }];
    render(<Tabs tabs={tabs} activeTab="tab1" onChange={onChange} />);
    fireEvent.click(screen.getByText('Tab 1'));
    expect(onChange).toHaveBeenCalledWith('tab1');
  });

  it('renders tab with count', () => {
    const tabs = [{ id: 'tab1', label: 'Tab 1', count: 5 }];
    render(<Tabs tabs={tabs} activeTab="tab1" onChange={() => {}} />);
    expect(screen.getByText('5')).toBeDefined();
  });
});

describe('Toggle', () => {
  it('renders with label', () => {
    render(<Toggle checked={false} onChange={() => {}} label="Toggle me" />);
    expect(screen.getByText('Toggle me')).toBeDefined();
  });

  it('calls onChange when clicked', () => {
    const onChange = vi.fn();
    render(<Toggle checked={false} onChange={onChange} label="Toggle" />);
    fireEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('does not call onChange when disabled', () => {
    const onChange = vi.fn();
    render(<Toggle checked={false} onChange={onChange} label="Toggle" disabled />);
    fireEvent.click(screen.getByRole('switch'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders with description', () => {
    render(<Toggle checked={false} onChange={() => {}} label="Toggle" description="Description text" />);
    expect(screen.getByText('Description text')).toBeDefined();
  });
});

describe('Slider', () => {
  it('renders with label', () => {
    render(<Slider value={50} onChange={() => {}} label="Volume" />);
    expect(screen.getByText('Volume')).toBeDefined();
  });

  it('renders value with unit', () => {
    const { container } = render(<Slider value={75} onChange={() => {}} unit="%" />);
    expect(container.textContent).toContain('75%');
  });

  it('renders description', () => {
    render(<Slider value={50} onChange={() => {}} description="Adjust volume" />);
    expect(screen.getByText('Adjust volume')).toBeDefined();
  });
});
