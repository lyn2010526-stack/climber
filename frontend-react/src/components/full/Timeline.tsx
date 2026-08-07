/* Timeline component */

import React, { useState, useEffect, useCallback, useMemo, useRef, useContext, createContext } from 'react';

interface TimelineProps {
  className?: string;
  disabled?: boolean;
  loading?: boolean;
  error?: string;
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  onChange?: (value: string) => void;
  onBlur?: () => void;
  onFocus?: () => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  onKeyUp?: (e: React.KeyboardEvent) => void;
  children?: React.ReactNode;
}

interface TimelineState {
  focused: boolean;
  hovered: boolean;
  active: boolean;
  value: string;
  error: string | null;
}

const TimelineContext = createContext<TimelineState | null>(null);

export default function Timeline(props: TimelineProps) {
  const {
    className = "",
    disabled = false,
    loading = false,
    error: externalError,
    value: controlledValue,
    defaultValue = "",
    placeholder = "",
    onChange,
    onBlur,
    onFocus,
    onKeyDown,
    onKeyUp,
    children,
  } = props;

  const [state, setState] = useState<TimelineState>({
    focused: false,
    hovered: false,
    active: false,
    value: defaultValue,
    error: externalError || null,
  });

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (controlledValue !== undefined) {
      setState(prev => ({ ...prev, value: controlledValue }));
    }
  }, [controlledValue]);

  useEffect(() => {
    if (externalError !== undefined) {
      setState(prev => ({ ...prev, error: externalError || null }));
    }
  }, [externalError]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setState(prev => ({ ...prev, value: newValue }));
    onChange?.(newValue);
  }, [onChange]);

  const handleFocus = useCallback(() => {
    setState(prev => ({ ...prev, focused: true }));
    onFocus?.();
  }, [onFocus]);

  const handleBlur = useCallback(() => {
    setState(prev => ({ ...prev, focused: false }));
    onBlur?.();
  }, [onBlur]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    setState(prev => ({ ...prev, active: true }));
    onKeyDown?.(e);
  }, [onKeyDown]);

  const handleKeyUp = useCallback((e: React.KeyboardEvent) => {
    setState(prev => ({ ...prev, active: false }));
    onKeyUp?.(e);
  }, [onKeyUp]);

  const handleMouseEnter = useCallback(() => {
    setState(prev => ({ ...prev, hovered: true }));
  }, []);

  const handleMouseLeave = useCallback(() => {
    setState(prev => ({ ...prev, hovered: false }));
  }, []);

  const isDisabled = disabled || loading;
  const hasError = state.error !== null;
  const isFocused = state.focused;
  const isHovered = state.hovered;
  const isActive = state.active;

  const containerClasses = useMemo(() => {
    return [
      className,
      isDisabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
      hasError ? "border-red-500" : isFocused ? "border-blue-500 ring-2 ring-blue-200" : "border-gray-300",
    ].join(" ");
  }, [className, isDisabled, hasError, isFocused]);

  return (
    <TimelineContext.Provider value={state}>
      <div
        ref={containerRef}
        className={containerClasses}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <input
          ref={inputRef}
          type="text"
          value={state.value}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          disabled={isDisabled}
          placeholder={placeholder}
          className="w-full px-3 py-2 border rounded-md focus:outline-none"
        />
        {loading && <span className="absolute right-3 top-2 animate-spin">...</span>}
        {hasError && <p className="text-red-500 text-sm mt-1">{state.error}</p>}
        {children}
      </div>
    </TimelineContext.Provider>
  );
}
