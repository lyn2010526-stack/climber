import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AnnotationPanel, buildAnnotationFeedback } from './AnnotationPanel';

const ANNOTATIONS = [
  { index: 1, note: 'Move the button up', x: 0.25, y: 0.4 },
  { index: 2, note: 'Fix the copy', x: 0.7, y: 0.8 },
];

describe('AnnotationPanel', () => {
  it('renders the image and one numbered card per annotation', () => {
    render(<AnnotationPanel imageUrl="data:image/png;base64,AAAA" annotations={ANNOTATIONS} onSubmit={vi.fn()} />);
    expect(screen.getByRole('img', { name: 'Annotated screenshot' })).toBeVisible();
    expect(screen.getByTestId('annotation-card-1')).toBeVisible();
    expect(screen.getByTestId('annotation-card-2')).toBeVisible();
    expect(screen.getByTestId('annotation-marker-1')).toBeVisible();
    expect(screen.getByTestId('annotation-marker-2')).toBeVisible();
  });

  it('shows a placeholder when no screenshot is attached', () => {
    render(<AnnotationPanel annotations={ANNOTATIONS} onSubmit={vi.fn()} />);
    expect(screen.getByText('No screenshot attached')).toBeVisible();
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('submits structured feedback with edited notes and coordinates', () => {
    const onSubmit = vi.fn();
    render(<AnnotationPanel annotations={ANNOTATIONS} source="clipboard" onSubmit={onSubmit} />);
    const card = screen.getByTestId('annotation-card-1');
    fireEvent.change(within(card).getByRole('textbox'), { target: { value: 'Move it down' } });
    fireEvent.click(screen.getByRole('button', { name: /Submit feedback/ }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      source: 'clipboard',
      annotations: [
        { index: 1, note: 'Move it down', x: 0.25, y: 0.4 },
        { index: 2, note: 'Fix the copy', x: 0.7, y: 0.8 },
      ],
    });
  });

  it('builds a normalized feedback object', () => {
    expect(buildAnnotationFeedback('screen', ANNOTATIONS)).toEqual({
      source: 'screen',
      annotations: ANNOTATIONS,
    });
  });
});
