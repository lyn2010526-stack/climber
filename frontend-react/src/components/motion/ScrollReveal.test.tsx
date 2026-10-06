import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ScrollReveal } from './ScrollReveal';

interface MockObserver {
  callback: (entries: IntersectionObserverEntry[]) => void;
  options: IntersectionObserverInit | undefined;
  targets: Element[];
  disconnected: boolean;
  observe: (target: Element) => void;
  unobserve: (target: Element) => void;
  disconnect: () => void;
  trigger: (isIntersecting: boolean) => void;
}

class MockIntersectionObserver {
  static instances: MockObserver[] = [];

  callback: (entries: IntersectionObserverEntry[]) => void;
  options: IntersectionObserverInit | undefined;
  targets: Element[] = [];
  disconnected = false;

  constructor(callback: (entries: IntersectionObserverEntry[]) => void, options?: IntersectionObserverInit) {
    this.callback = callback;
    this.options = options;
    MockIntersectionObserver.instances.push(this);
  }

  observe(target: Element) {
    this.targets.push(target);
  }

  unobserve() {}

  disconnect() {
    this.disconnected = true;
  }

  trigger(isIntersecting: boolean) {
    for (const target of this.targets) {
      this.callback([
        {
          isIntersecting,
          target,
          intersectionRatio: isIntersecting ? 1 : 0,
          time: 0,
          boundingClientRect: target.getBoundingClientRect(),
          intersectionRect: target.getBoundingClientRect(),
          rootBounds: null,
        } as IntersectionObserverEntry,
      ]);
    }
  }
}

function stubObserver() {
  vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
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

function lastObserver(): MockObserver {
  return MockIntersectionObserver.instances[MockIntersectionObserver.instances.length - 1];
}

beforeEach(() => {
  MockIntersectionObserver.instances.length = 0;
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('ScrollReveal with observer', () => {
  it('renders hidden initially and reveals on intersection', () => {
    stubObserver();
    render(
      <ScrollReveal testId="reveal">
        <p>content</p>
      </ScrollReveal>,
    );
    const node = screen.getByTestId('reveal');
    expect(node.style.opacity).toBe('0');
    expect(node.style.transform).toBe('translate3d(0, 16px, 0)');
    expect(node.style.transition).toContain('opacity 480ms');
    expect(node.style.transition).toContain('var(--ease-spring)');

    act(() => {
      lastObserver().trigger(true);
    });
    expect(node.style.opacity).toBe('1');
    expect(node.style.transform).toBe('none');
  });

  it('passes the offset as rootMargin and disconnects on unmount', () => {
    stubObserver();
    const { unmount } = render(
      <ScrollReveal testId="reveal" offset="0px 0px -8% 0px">
        <p>content</p>
      </ScrollReveal>,
    );
    expect(lastObserver().options?.rootMargin).toBe('0px 0px -8% 0px');
    expect(lastObserver().disconnected).toBe(false);
    unmount();
    expect(lastObserver().disconnected).toBe(true);
  });

  it('stays revealed when once is true and the element leaves the viewport', () => {
    stubObserver();
    render(
      <ScrollReveal testId="reveal" once>
        <p>content</p>
      </ScrollReveal>,
    );
    const observer = lastObserver();
    act(() => {
      observer.trigger(true);
    });
    expect(observer.disconnected).toBe(true);
    act(() => {
      observer.trigger(false);
    });
    expect(screen.getByTestId('reveal').style.opacity).toBe('1');
  });

  it('re-hides when once is false and the element leaves the viewport', () => {
    stubObserver();
    render(
      <ScrollReveal testId="reveal" once={false}>
        <p>content</p>
      </ScrollReveal>,
    );
    const observer = lastObserver();
    act(() => {
      observer.trigger(true);
    });
    expect(screen.getByTestId('reveal').style.opacity).toBe('1');
    act(() => {
      observer.trigger(false);
    });
    expect(screen.getByTestId('reveal').style.opacity).toBe('0');
    expect(observer.disconnected).toBe(false);
  });

  it('applies directional transforms from distance and direction', () => {
    stubObserver();
    render(
      <ScrollReveal testId="reveal" direction="left" distance={40} duration={900} delay={120} ease="var(--ease-out)">
        <p>content</p>
      </ScrollReveal>,
    );
    const node = screen.getByTestId('reveal');
    expect(node.style.transform).toBe('translate3d(40px, 0, 0)');
    expect(node.style.transition).toContain('900ms');
    expect(node.style.transition).toContain('120ms');
    expect(node.style.transition).toContain('var(--ease-out)');
  });

  it('staggers child transition delays while leaving the wrapper clean', () => {
    stubObserver();
    render(
      <ScrollReveal testId="reveal" stagger={70} delay={10}>
        <p data-testid="item-0">one</p>
        <p data-testid="item-1">two</p>
        <p data-testid="item-2">three</p>
      </ScrollReveal>,
    );
    const wrapper = screen.getByTestId('reveal');
    expect(wrapper.style.opacity).toBe('');
    expect(screen.getByTestId('item-0').style.transitionDelay).toBe('10ms');
    expect(screen.getByTestId('item-1').style.transitionDelay).toBe('80ms');
    expect(screen.getByTestId('item-2').style.transitionDelay).toBe('150ms');
    expect(screen.getByTestId('item-1').style.opacity).toBe('0');

    act(() => {
      lastObserver().trigger(true);
    });
    expect(screen.getByTestId('item-2').style.opacity).toBe('1');
    expect(screen.getByTestId('item-2').style.transform).toBe('none');
  });
});

describe('ScrollReveal degraded rendering', () => {
  it('renders a plain container when IntersectionObserver is unavailable', () => {
    render(
      <ScrollReveal testId="reveal">
        <p>content</p>
      </ScrollReveal>,
    );
    const node = screen.getByTestId('reveal');
    expect(node.style.opacity).toBe('');
    expect(node).toHaveTextContent('content');
    expect(MockIntersectionObserver.instances.length).toBe(0);
  });

  it('renders a plain container when the user prefers reduced motion', () => {
    stubObserver();
    stubReducedMotion(true);
    render(
      <ScrollReveal testId="reveal">
        <p>content</p>
      </ScrollReveal>,
    );
    const node = screen.getByTestId('reveal');
    expect(node.style.opacity).toBe('');
    expect(node).toHaveTextContent('content');
    expect(MockIntersectionObserver.instances.length).toBe(0);
  });

  it('renders a plain container with stagger children untouched under reduced motion', () => {
    stubObserver();
    stubReducedMotion(true);
    render(
      <ScrollReveal testId="reveal" stagger={70}>
        <p data-testid="item-0">one</p>
      </ScrollReveal>,
    );
    expect(screen.getByTestId('item-0').style.transitionDelay).toBe('');
    expect(screen.getByTestId('item-0').style.opacity).toBe('');
  });
});
