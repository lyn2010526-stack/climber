import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Timeline, TimelineItem, TimelineDot, TimelineLine, TimelineContent } from '../Timeline';

describe('Timeline', () => {
  it('renders children', () => {
    render(
      <Timeline>
        <TimelineItem>Content</TimelineItem>
      </Timeline>
    );
    expect(screen.getByText('Content')).toBeDefined();
  });

  it('renders timeline item with dot and content', () => {
    render(
      <Timeline>
        <TimelineItem>
          <TimelineDot status="success" />
          <TimelineLine />
          <TimelineContent title="完成部署" description="部署到生产环境成功" timestamp="2小时前" />
        </TimelineItem>
      </Timeline>
    );
    expect(screen.getByText('完成部署')).toBeDefined();
    expect(screen.getByText('部署到生产环境成功')).toBeDefined();
    expect(screen.getByText('2小时前')).toBeDefined();
  });

  it('renders multiple timeline items', () => {
    render(
      <Timeline>
        <TimelineItem>
          <TimelineDot status="success" />
          <TimelineContent title="第一步" />
        </TimelineItem>
        <TimelineItem>
          <TimelineDot status="pending" />
          <TimelineContent title="第二步" />
        </TimelineItem>
        <TimelineItem>
          <TimelineDot status="error" />
          <TimelineContent title="第三步" />
        </TimelineItem>
      </Timeline>
    );
    expect(screen.getByText('第一步')).toBeDefined();
    expect(screen.getByText('第二步')).toBeDefined();
    expect(screen.getByText('第三步')).toBeDefined();
  });

  it('renders dot with different statuses', () => {
    const { container } = render(
      <TimelineDot status="warning" />
    );
    expect(container.querySelector('.bg-amber-500')).not.toBeNull();
  });

  it('renders dot with icon', () => {
    render(
      <TimelineDot status="info" icon={<span>icon</span>} />
    );
    expect(screen.getByText('icon')).toBeDefined();
  });
});
