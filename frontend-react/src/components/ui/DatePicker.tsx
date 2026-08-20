import { useState, useRef, useEffect, forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Calendar, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { cn } from '../../lib/utils';

const datePickerVariants = cva(
  'flex w-full rounded-lg border bg-white/[0.03] px-3 py-2 text-sm transition-all duration-200 text-white placeholder:text-white/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-blue-500/50 disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      inputSize: {
        sm: 'h-8 px-2.5 text-xs',
        md: 'h-10 px-3 text-sm',
        lg: 'h-12 px-4 text-base',
      },
    },
    defaultVariants: {
      inputSize: 'md',
    },
  }
);

interface DatePickerProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'size'>, VariantProps<typeof datePickerVariants> {
  value?: Date | null;
  onChange?: (date: Date | null) => void;
  placeholder?: string;
  format?: string;
  minDate?: Date;
  maxDate?: Date;
  clearable?: boolean;
}

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'];
const MONTHS = [
  '一月', '二月', '三月', '四月', '五月', '六月',
  '七月', '八月', '九月', '十月', '十一月', '十二月',
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
}

function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

const DatePicker = forwardRef<HTMLInputElement, DatePickerProps>(
  ({ value, onChange, placeholder = '选择日期', minDate, maxDate, clearable = true, className, inputSize, ...props }, ref) => {
    const [isOpen, setIsOpen] = useState(false);
    const [viewDate, setViewDate] = useState(value || new Date());
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (value) setViewDate(value);
    }, [value]);

    useEffect(() => {
      function handleClickOutside(e: MouseEvent) {
        if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
          setIsOpen(false);
        }
      }
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelectDate = (day: number) => {
      const newDate = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
      if (minDate && newDate < minDate) return;
      if (maxDate && newDate > maxDate) return;
      onChange?.(newDate);
      setIsOpen(false);
    };

    const handleClear = (e: React.MouseEvent) => {
      e.stopPropagation();
      onChange?.(null);
    };

    const prevMonth = () => {
      setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
    };

    const nextMonth = () => {
      setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));
    };

    const daysInMonth = getDaysInMonth(viewDate.getFullYear(), viewDate.getMonth());
    const firstDay = getFirstDayOfMonth(viewDate.getFullYear(), viewDate.getMonth());
    const today = new Date();

    const isDisabled = (day: number): boolean => {
      const d = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
      if (minDate && d < minDate) return true;
      if (maxDate && d > maxDate) return true;
      return false;
    };

    return (
      <div ref={containerRef} className="relative w-full">
        <div className="relative">
          <input
            ref={ref}
            type="text"
            readOnly
            value={value ? formatDate(value) : ''}
            placeholder={placeholder}
            onClick={() => setIsOpen(!isOpen)}
            className={cn(datePickerVariants({ inputSize }), 'cursor-pointer pr-10', className)}
            {...props}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {value && clearable && (
              <button
                type="button"
                onClick={handleClear}
                className="p-0.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors"
                aria-label="清除日期"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            <Calendar className="h-4 w-4 text-white/40" />
          </div>
        </div>

        {isOpen && (
          <div className="absolute z-50 mt-2 w-72 rounded-xl border border-white/[0.08] bg-[#1a1a2e] p-3 shadow-xl shadow-black/40 animate-in fade-in slide-in-from-top-1 duration-200">
            <div className="flex items-center justify-between mb-3">
              <button
                type="button"
                onClick={prevMonth}
                className="p-1 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors"
                aria-label="上个月"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm font-medium text-white">
                {viewDate.getFullYear()}年 {MONTHS[viewDate.getMonth()]}
              </span>
              <button
                type="button"
                onClick={nextMonth}
                className="p-1 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors"
                aria-label="下个月"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <div className="grid grid-cols-7 gap-0.5 mb-2">
              {WEEKDAYS.map((wd) => (
                <div key={wd} className="h-8 flex items-center justify-center text-xs text-white/40 font-medium">
                  {wd}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-0.5">
              {Array.from({ length: firstDay }).map((_, i) => (
                <div key={`empty-${i}`} className="h-8" />
              ))}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1;
                const currentDate = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
                const selected = value && isSameDay(currentDate, value);
                const isToday = isSameDay(currentDate, today);
                const disabled = isDisabled(day);

                return (
                  <button
                    key={day}
                    type="button"
                    disabled={disabled}
                    onClick={() => handleSelectDate(day)}
                    aria-label={`${viewDate.getFullYear()}年${viewDate.getMonth() + 1}月${day}日`}
                    aria-pressed={Boolean(selected)}
                    className={cn(
                      'h-8 w-full rounded-lg text-sm transition-all duration-150',
                      'flex items-center justify-center',
                      disabled && 'text-white/20 cursor-not-allowed',
                      !disabled && !selected && 'text-white/80 hover:bg-white/10',
                      isToday && !selected && 'ring-1 ring-blue-500/50 text-blue-400',
                      selected && 'bg-gradient-to-r from-blue-500 to-violet-500 text-white font-medium shadow-md shadow-blue-500/20',
                    )}
                  >
                    {day}
                  </button>
                );
              })}
            </div>

            <div className="mt-3 pt-2 border-t border-white/[0.06] flex justify-between">
              <button
                type="button"
                onClick={() => {
                  onChange?.(new Date());
                  setIsOpen(false);
                }}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                今天
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-xs text-white/40 hover:text-white/60 transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }
);
DatePicker.displayName = 'DatePicker';

export { DatePicker, datePickerVariants };
export type { DatePickerProps };
