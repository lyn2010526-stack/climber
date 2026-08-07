import React, { useEffect, useRef } from 'react';

/**
 * Focus Management Utilities
 */

// Store reference to element that had focus before dialog opened
let previousFocusElement: HTMLElement | null = null;

export const usePreviousFocus = () => {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    return () => {
      // Restore focus when component unmounts or when dialog closes
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, []);

  return previousFocusRef;
};

/**
 * Save current focus and restore it later
 */
export const saveFocus = (): void => {
  previousFocusElement = document.activeElement as HTMLElement;
};

/**
 * Restore saved focus
 */
export const restoreFocus = (): void => {
  if (previousFocusElement) {
    previousFocusElement.focus();
    previousFocusElement = null;
  }
};

/**
 * Get all focusable elements within a container
 */
export const getFocusableElements = (container: HTMLElement): HTMLElement[] => {
  const focusableSelectors = [
    'button:not([disabled])',
    '[href]:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"]):not([disabled])',
    'video:not([disabled])',
    'audio:not([disabled])',
    '[contenteditable]:not([contenteditable="false"])',
  ].join(', ');

  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors)).filter(
    (el) => {
      return el.offsetParent !== null; // Hidden elements are not focusable
    }
  );
};

/**
 * Force focus on an element without triggering scroll
 */
export const forceFocusWithoutScroll = (element: HTMLElement): void => {
  element.tabIndex = -1;
  element.focus({ preventScroll: true });
  element.removeAttribute('tabIndex');
};

/**
 * Check if element is visible (for focusing purposes)
 */
export const isElementVisible = (element: Element | null): boolean => {
  if (!element || !(element instanceof HTMLElement)) return false;
  
  const style = window.getComputedStyle(element);
  return (
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    element.offsetParent !== null
  );
};
