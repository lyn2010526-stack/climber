import { act, fireEvent, render, screen } from '@testing-library/react';
import { useRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Parallax } from './Parallax';

const rafFlush = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

function stubRect(element: Element, top: number, height: number) {
  return vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({
    top,
    height,
    bottom: top + height,
    left: 0,
    right: 0,
    width: 0,
    x: 0,
    y: top,
    toJSON: () => ({}),
  } as DOMRect);
}

function stubReducedMotion(matches: boolean) {
  vi.spyOn(window, 'matchMedia').mockImplementation((() => ({
    matches,
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia);
}

function ParallaxHarness({ container }: { container?: 'inside' }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  return (
    <div>
      <div ref={containerRef} data-testid="host" style={{ height: 200, overflow: 'auto' }}>
        <Parallax testId="parallax" containerRef={container ? containerRef : undefined} speed={0.5} maxShift={200}>
          <span>decoration</span>
        </Parallax>
      </div>
    </div>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Parallax window drift', () => {
  it('translates the node relative to the viewport center on mount', async () => {
    render(<ParallaxHarness />);
    const node = screen.getByTestId('parallax');
    const rectSpy = stubRect(node, 100, 40);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('translate3d(0, -132.00px, 0)');
    expect(rectSpy).toHaveBeenCalled();
  });

  it('updates the transform on window scroll and coalesces frames', async () => {
    render(<ParallaxHarness />);
    const node = screen.getByTestId('parallax');
    const rectSpy = stubRect(node, 100, 40);
    await act(async () => {
      await rafFlush();
    });
    rectSpy.mockClear();
    rectSpy.mockReturnValue({
      top: 500,
      height: 40,
      bottom: 540,
      left: 0,
      right: 0,
      width: 0,
      x: 0,
      y: 500,
      toJSON: () => ({}),
    } as DOMRect);
    fireEvent.scroll(window);
    fireEvent.scroll(window);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('translate3d(0, 68.00px, 0)');
    expect(rectSpy).toHaveBeenCalledTimes(1);
  });

  it('clamps the drift to maxShift', async () => {
    render(<Parallax testId="parallax" speed={0.5} />);
    const node = screen.getByTestId('parallax');
    stubRect(node, 100, 40);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('translate3d(0, -40.00px, 0)');
  });

  it('clears the transform on unmount', async () => {
    const { unmount } = render(<ParallaxHarness />);
    const node = screen.getByTestId('parallax');
    stubRect(node, 100, 40);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).not.toBe('');
    unmount();
    expect(node.style.transform).toBe('');
  });
});

describe('Parallax container binding', () => {
  it('listens to the container element instead of the window', async () => {
    render(<ParallaxHarness container="inside" />);
    const node = screen.getByTestId('parallax');
    const host = screen.getByTestId('host');
    const rectSpy = stubRect(node, 80, 20);
    stubRect(host, 0, 200);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('translate3d(0, -5.00px, 0)');
    rectSpy.mockReturnValue({
      top: 240,
      height: 20,
      bottom: 260,
      left: 0,
      right: 0,
      width: 0,
      x: 0,
      y: 240,
      toJSON: () => ({}),
    } as DOMRect);
    fireEvent.scroll(window);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('translate3d(0, -5.00px, 0)');
    fireEvent.scroll(host);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('translate3d(0, 75.00px, 0)');
  });
});

describe('Parallax degradation', () => {
  it('applies no transform when the user prefers reduced motion', async () => {
    stubReducedMotion(true);
    render(<ParallaxHarness />);
    const node = screen.getByTestId('parallax');
    stubRect(node, 100, 40);
    await act(async () => {
      await rafFlush();
    });
    fireEvent.scroll(window);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('');
  });

  it('applies no transform when speed is zero', async () => {
    render(<Parallax testId="parallax" speed={0} />);
    const node = screen.getByTestId('parallax');
    stubRect(node, 100, 40);
    await act(async () => {
      await rafFlush();
    });
    expect(node.style.transform).toBe('');
  });

  it('stays hidden from accessibility tree when ariaHidden is set', () => {
    render(
      <Parallax testId="parallax" ariaHidden>
        <span>decoration</span>
      </Parallax>,
    );
    expect(screen.getByTestId('parallax')).toHaveAttribute('aria-hidden', 'true');
  });
});
