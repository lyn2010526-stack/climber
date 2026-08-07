/* Generic data table component */

import React, { useState, useEffect, useCallback, useRef } from 'react';

interface TableProps {
  /** Additional CSS class names. */
  className?: string;
  /** Whether the component is disabled. */
  disabled?: boolean;
  /** Click handler. */
  onClick?: () => void;
  /** Change handler. */
  onChange?: (value: string) => void;
  /** Child elements. */
  children?: React.ReactNode;
}

/** Generic data table component. */
export default function Table(props: TableProps) {
  const { className = "", disabled = false, onClick, onChange, children } = props;
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
    onChange?.(e.target.value);
  }, [onChange]);

  const handleClick = useCallback(() => {
    if (!disabled) {
      onClick?.();
    }
  }, [disabled, onClick]);

  const handleFocus = useCallback(() => {
    setFocused(true);
  }, []);

  const handleBlur = useCallback(() => {
    setFocused(false);
  }, []);

  useEffect(() => {
    if (focused && inputRef.current) {
      inputRef.current.focus();
    }
  }, [focused]);

  return (
    <div
      className={`${className} ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        disabled={disabled}
        className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${focused ? "border-blue-500" : "border-gray-300"}`}
        placeholder="Enter value..."
      />
      {children}
    </div>
  );
}
