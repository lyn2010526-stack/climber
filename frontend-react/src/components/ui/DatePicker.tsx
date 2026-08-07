import React, { useState, useRef, useEffect, useId, useCallback } from 'react';
import { cn } from '../../lib/utils';
import { ChevronLeft, ChevronRight, Calendar, X } from 'lucide-react';

export interface DatePickerProps {
  value?: Date | null;
  onChange?: (date: Date | null) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  minDate?: Date;
  maxDate?: Date;
  disabledDates?: Date[];
  clearable?: boolean;
  id?: string;
  required?: boolean;
}

const DatePicker: React.FC<DatePickerProps> = ({
  value,
  onChange,
  placeholder = 'Select date',
  disabled = false,
  error,
  label,
  size = 'md',
  className,
  minDate,
  maxDate,
  disabledDates = [],
  clearable = true,
  id,
  required = false,
}) => {
  const [open, setOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(value || new Date());
  const containerRef = useRef<HTMLDivElement>(null);
  const generatedId = useId();
  const pickerId = id || generatedId;

  const daysInMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).getDate();
  const firstDayOfMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1).getDay();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const isDateDisabled = useCallback((date: Date) => {
    if (minDate && date < minDate) return true;
    if (maxDate && date > maxDate) return true;
    return disabledDates.some(d => d.toDateString() === date.toDateString());
  }, [minDate, maxDate, disabledDates]);

  const isDateSelected = useCallback((date: Date) => {
    return value?.toDateString() === date.toDateString();
  }, [value]);

  const handleSelectDate = useCallback((day: number) => {
    const selected = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
    if (isDateDisabled(selected)) return;
    onChange?.(selected);
    setOpen(false);
  }, [currentMonth, isDateDisabled, onChange]);

  const handleClear = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onChange?.(null);
  }, [onChange]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const dayNames = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

  const inputSizeClasses = {
    sm: 'h-[var(--size-sm)] px-[var(--space-2-5)] text-[var(--font-size-xs)]',
    md: 'h-[var(--size-md)] px-[var(--space-3)] text-[var(--font-size-sm)]',
    lg: 'h-[var(--size-lg)] px-[var(--space-4)] text-[var(--font-size-base)]',
  };

  return (
    <div className="flex flex-col gap-[var(--space-1-5)] w-full" ref={containerRef}>
      {label && (
        <label htmlFor={pickerId} className="text-[var(--font-size-sm)] font-medium text-[var(--text-primary)]">
          {label}
          {required && <span className="text-[var(--color-danger)] ml-[var(--space-0-5)]">*</span>}
        </label>
      )}
      <div className="relative">
        <button
          id={pickerId}
          type="button"
          disabled={disabled}
          onClick={() => !disabled && setOpen(!open)}
          className={cn(
            'flex w-full items-center justify-between border bg-[var(--surface-bg)] rounded-[var(--radius-lg)] transition-all duration-[var(--transition-normal)]',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]/20 focus-visible:border-[var(--border-focus)]',
            'disabled:cursor-not-allowed disabled:bg-[var(--surface-bg-disabled)] disabled:text-[var(--text-disabled)] disabled:opacity-60',
            inputSizeClasses[size],
            error ? 'border-[var(--border-error)]' : 'border-[var(--border-default)]',
            open && 'border-[var(--border-focus)] ring-2 ring-[var(--focus-ring-color)]/20'
          )}
          aria-haspopup="dialog"
          aria-expanded={open}
        >
          <span className={cn('flex items-center gap-[var(--space-2)]', !value && 'text-[var(--text-muted)]')}>
            <Calendar className="w-[var(--icon-sm)] h-[var(--icon-sm)] text-[var(--text-muted)]" />
            {value ? value.toLocaleDateString() : placeholder}
          </span>
          {clearable && value && (
            <span
              onClick={handleClear}
              className="p-[var(--space-0-5)] rounded-full hover:bg-[var(--surface-bg-hover)] text-[var(--text-muted)]"
              role="button"
              aria-label="Clear date"
            >
              <X className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />
            </span>
          )}
        </button>

        {open && (
          <div
            className="absolute z-[var(--z-dropdown)] mt-[var(--space-1)] p-[var(--space-4)] bg-[var(--surface-elevated)] border border-[var(--border-subtle)] rounded-[var(--radius-xl)] shadow-[var(--shadow-xl)] w-[320px] animate-[scaleIn_150ms_cubic-bezier(0.16,1,0.3,1)]"
            role="dialog"
            aria-label="Date picker"
          >
            <div className="flex items-center justify-between mb-[var(--space-3)]">
              <button
                onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))}
                className="p-[var(--space-1)] rounded-[var(--radius-md)] hover:bg-[var(--surface-bg-hover)] text-[var(--text-secondary)]"
                aria-label="Previous month"
              >
                <ChevronLeft className="w-[var(--icon-md)] h-[var(--icon-md)]" />
              </button>
              <span className="text-[var(--font-size-sm)] font-medium text-[var(--text-primary)]">
                {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
              </span>
              <button
                onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))}
                className="p-[var(--space-1)] rounded-[var(--radius-md)] hover:bg-[var(--surface-bg-hover)] text-[var(--text-secondary)]"
                aria-label="Next month"
              >
                <ChevronRight className="w-[var(--icon-md)] h-[var(--icon-md)]" />
              </button>
            </div>

            <div className="grid grid-cols-7 gap-[var(--space-0-5)] mb-[var(--space-1)]">
              {dayNames.map(day => (
                <div key={day} className="text-center text-[10px] font-semibold text-[var(--text-muted)] py-[var(--space-1)]">
                  {day}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-[var(--space-0-5)]">
              {Array.from({ length: firstDayOfMonth }).map((_, i) => (
                <div key={`empty-${i}`} />
              ))}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1;
                const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
                const isDisabled = isDateDisabled(date);
                const isSelected = isDateSelected(date);
                const isToday = date.toDateString() === today.toDateString();

                return (
                  <button
                    key={day}
                    onClick={() => handleSelectDate(day)}
                    disabled={isDisabled}
                    className={cn(
                      'h-8 w-8 rounded-[var(--radius-md)] text-[var(--font-size-xs)] font-medium transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]',
                      isSelected && 'bg-[var(--accent)] text-white',
                      !isSelected && !isDisabled && 'text-[var(--text-primary)] hover:bg-[var(--surface-bg-hover)]',
                      isDisabled && 'text-[var(--text-disabled)] cursor-not-allowed opacity-40',
                      isToday && !isSelected && 'ring-1 ring-[var(--accent)]'
                    )}
                    aria-label={date.toLocaleDateString()}
                    aria-selected={isSelected}
                  >
                    {day}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
      {error && <p className="text-[var(--font-size-xs)] text-[var(--color-danger)]" role="alert">{error}</p>}
    </div>
  );
};

export { DatePicker };
