import React, { useEffect } from 'react';

/**
 * Keyboard Navigation Handler
 * Provides consistent keyboard navigation patterns
 */
type KeyboardNavProps = {
  onNavigateUp?: () => void;
  onNavigateDown?: () => void;
  onNavigateLeft?: () => void;
  onNavigateRight?: () => void;
  onEnter?: () => void;
  onSpace?: (e: KeyboardEvent) => void;
  onEscape?: () => void;
  onFocusNext?: () => void;
  onFocusPrevious?: () => void;
  enabled?: boolean;
};

export const KeyboardNav: React.FC<KeyboardNavProps> = ({
  onNavigateUp,
  onNavigateDown,
  onNavigateLeft,
  onNavigateRight,
  onEnter,
  onSpace,
  onEscape,
  onFocusNext,
  onFocusPrevious,
  enabled = true,
}) => {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault();
          onNavigateUp?.();
          break;
        case 'ArrowDown':
          e.preventDefault();
          onNavigateDown?.();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          onNavigateLeft?.();
          break;
        case 'ArrowRight':
          e.preventDefault();
          onNavigateRight?.();
          break;
        case 'Enter':
          e.preventDefault();
          onEnter?.();
          break;
        case ' ': // Spacebar
          e.preventDefault();
          onSpace?.(e);
          break;
        case 'Escape':
          e.preventDefault();
          onEscape?.();
          break;
        case 'Tab':
          if (onFocusNext && !e.shiftKey) {
            // Allow default tab behavior
          } else if (onFocusPrevious && e.shiftKey) {
            // Allow default shift+tab behavior
          }
          break;
        default:
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enabled, onNavigateUp, onNavigateDown, onNavigateLeft, onNavigateRight, onEnter, onSpace, onEscape, onFocusNext, onFocusPrevious]);

  return null;
};

/**
 * Custom hook for keyboard navigation in lists and menus
 */
export const useKeyboardListNavigation = ({
  itemCount,
  selectedIndex,
  onSelectedChange,
}: {
  itemCount: number;
  selectedIndex: number;
  onSelectedChange: (index: number) => void;
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (itemCount === 0) return;

      let newIndex = selectedIndex;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          newIndex = Math.min(selectedIndex + 1, itemCount - 1);
          break;
        case 'ArrowUp':
          e.preventDefault();
          newIndex = Math.max(selectedIndex - 1, 0);
          break;
        case 'Home':
          e.preventDefault();
          newIndex = 0;
          break;
        case 'End':
          e.preventDefault();
          newIndex = itemCount - 1;
          break;
        case 'Enter':
        case ' ':
          if (selectedIndex >= 0) {
            e.preventDefault();
            onSelectedChange(selectedIndex);
          }
          return;
        default:
          return;
      }

      if (newIndex !== selectedIndex) {
        onSelectedChange(newIndex);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [itemCount, selectedIndex, onSelectedChange]);
};
