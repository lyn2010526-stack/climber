import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computeTypewriterStep, useTypewriterReveal } from './useTypewriterReveal';

type FrameCallback = FrameRequestCallback;

let frames: FrameCallback[];
const frameIds = new Map<number, FrameCallback>();
let clock = 0;

function runFrame(): void {
  const next = frames.shift();
  if (!next) return;
  clock += 16;
  act(() => { next(clock); });
}

function drainFrames(maxFrames = 400): void {
  for (let i = 0; i < maxFrames && frames.length > 0; i += 1) runFrame();
}

beforeEach(() => {
  frames = [];
  frameIds.clear();
  clock = 0;
  vi.stubGlobal('requestAnimationFrame', (callback: FrameCallback) => {
    const id = frameIds.size + 1;
    frameIds.set(id, callback);
    frames.push(callback);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => {
    const callback = frameIds.get(id);
    if (callback) {
      frames = frames.filter(pending => pending !== callback);
      frameIds.delete(id);
    }
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('computeTypewriterStep', () => {
  it('reveals at least one grapheme per frame while a backlog exists', () => {
    expect(computeTypewriterStep(10, 80, 16)).toBe(1);
    expect(computeTypewriterStep(1, 80, 16)).toBe(1);
  });

  it('bounds the reveal by the steady chars-per-second rate', () => {
    expect(computeTypewriterStep(1000, 480, 1000)).toBe(480);
    expect(computeTypewriterStep(100, 480, 1000)).toBe(100);
  });

  it('never reveals when the stream is idle or empty', () => {
    expect(computeTypewriterStep(0, 80, 16)).toBe(0);
    expect(computeTypewriterStep(10, 0, 16)).toBe(0);
    expect(computeTypewriterStep(10, 80, 0)).toBe(0);
  });
});

describe('useTypewriterReveal', () => {
  it('shows content in full when the stream is not active', () => {
    const { result } = renderHook(({ content, active }) => useTypewriterReveal(content, { active }), {
      initialProps: { content: 'final answer', active: false },
    });
    expect(result.current).toBe('final answer');
  });

  it('reveals a live stream gradually and catches up completely', () => {
    const { result, rerender } = renderHook(
      ({ content, active }) => useTypewriterReveal(content, { active, preset: 'balanced' }),
      { initialProps: { content: '', active: true } },
    );
    rerender({ content: 'Hello Codex', active: true });
    runFrame();
    expect(result.current.length).toBeGreaterThan(0);
    expect(result.current).not.toBe('Hello Codex');
    drainFrames();
    expect(result.current).toBe('Hello Codex');
    expect(frames).toHaveLength(0);
  });

  it('appends new streamed text onto the partially revealed content', () => {
    const { result, rerender } = renderHook(
      ({ content, active }) => useTypewriterReveal(content, { active, preset: 'silky' }),
      { initialProps: { content: 'Hello ', active: true } },
    );
    rerender({ content: 'Hello ', active: true });
    runFrame();
    expect(result.current.length).toBeGreaterThan(0);
    rerender({ content: 'Hello Codex', active: true });
    drainFrames();
    expect(result.current).toBe('Hello Codex');
  });

  it('flushes the full text immediately when the stream stops', () => {
    const { result, rerender } = renderHook(
      ({ content, active }) => useTypewriterReveal(content, { active, preset: 'balanced' }),
      { initialProps: { content: '', active: true } },
    );
    rerender({ content: 'interrupted mid-way', active: true });
    runFrame();
    expect(result.current.length).toBeLessThan('interrupted mid-way'.length);
    rerender({ content: 'interrupted mid-way', active: false });
    expect(result.current).toBe('interrupted mid-way');
    expect(frames).toHaveLength(0);
  });

  it('respects reduced motion and the master switch with full content', () => {
    const { result, rerender } = renderHook(
      ({ content }) => useTypewriterReveal(content, { active: true, enabled: false }),
      { initialProps: { content: '' } },
    );
    rerender({ content: 'disabled reveal' });
    expect(result.current).toBe('disabled reveal');

    const reduced = renderHook(
      ({ content }) => useTypewriterReveal(content, { active: true, reducedMotion: true }),
      { initialProps: { content: '' } },
    );
    reduced.rerender({ content: 'reduced motion' });
    expect(reduced.result.current).toBe('reduced motion');
    expect(frames).toHaveLength(0);
  });

  it('does not leave a trailing frame scheduled after completion', () => {
    const { result, rerender } = renderHook(
      ({ content, active }) => useTypewriterReveal(content, { active, preset: 'realtime' }),
      { initialProps: { content: '', active: true } },
    );
    rerender({ content: 'done', active: true });
    drainFrames();
    expect(result.current).toBe('done');
    expect(frames).toHaveLength(0);
  });
});