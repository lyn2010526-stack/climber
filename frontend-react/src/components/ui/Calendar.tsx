import React, { useState, useMemo, useCallback } from 'react';
import { cn } from '../../lib/utils';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';

export interface CalendarEvent {
  id: string;
  title: string;
  date: string;
  color?: string;
  description?: string;
}

export interface CalendarProps {
  events?: CalendarEvent[];
  initialDate?: Date;
  view?: 'month' | 'week';
  onDateClick?: (date: string) => void;
  onEventClick?: (event: CalendarEvent) => void;
  onAddEvent?: (date: string) => void;
  onViewChange?: (view: 'month' | 'week') => void;
  className?: string;
  weekStartsOn?: 0 | 1;
  minDate?: string;
  maxDate?: string;
}

const WEEKDAYS_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

function formatDate(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function Calendar({
  events = [],
  initialDate = new Date(),
  view = 'month',
  onDateClick,
  onEventClick,
  onAddEvent,
  onViewChange,
  className,
  weekStartsOn = 0,
}: CalendarProps) {
  const [currentDate, setCurrentDate] = useState(initialDate);
  const [currentView, setCurrentView] = useState(view);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const daysInMonth = useMemo(() => getDaysInMonth(year, month), [year, month]);
  const firstDay = useMemo(() => getFirstDayOfMonth(year, month), [year, month]);

  const today = new Date();
  const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());

  const eventsByDate = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    events.forEach(event => {
      const list = map[event.date];
      if (!list) map[event.date] = [event];
      else list.push(event);
    });
    return map;
  }, [events]);

  const navigateMonth = useCallback((direction: number) => {
    setCurrentDate(new Date(year, month + direction, 1));
  }, [year, month]);

  const navigateWeek = useCallback((direction: number) => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate() + direction * 7));
  }, [currentDate]);

  const handleViewChange = useCallback((newView: 'month' | 'week') => {
    setCurrentView(newView);
    onViewChange?.(newView);
  }, [onViewChange]);

  const renderMonthView = () => {
    const cells: React.ReactNode[] = [];
    const offset = (firstDay - weekStartsOn + 7) % 7;

    for (let i = 0; i < offset; i++) {
      cells.push(<div key={`empty-${i}`} className="min-h-[100px] border-b border-r border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)]/30" />);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = formatDate(year, month, day);
      const dayEvents = eventsByDate[dateStr] || [];
      const isToday = dateStr === todayStr;

      cells.push(
        <div
          key={day}
          className={cn(
            'min-h-[100px] border-b border-r border-[var(--border-subtle)] p-1.5 transition-colors hover:bg-[var(--surface-bg-hover)] cursor-pointer group',
            isToday && 'bg-[var(--accent)]/5'
          )}
          onClick={() => onDateClick?.(dateStr)}
          role="gridcell"
          aria-label={`${MONTHS[month]} ${day}, ${year}`}
          tabIndex={0}
        >
          <div className="flex items-center justify-between mb-1">
            <span className={cn(
              'text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full',
              isToday ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)]'
            )}>
              {day}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onAddEvent?.(dateStr); }}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-[var(--surface-bg-hover)] text-[var(--text-muted)] transition-opacity"
              aria-label={`Add event on ${dateStr}`}
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="space-y-0.5">
            {dayEvents.slice(0, 3).map(event => (
              <button
                key={event.id}
                onClick={(e) => { e.stopPropagation(); onEventClick?.(event); }}
                className="w-full text-left text-[10px] px-1.5 py-0.5 rounded truncate transition-colors hover:opacity-80"
                style={{ backgroundColor: event.color || 'var(--accent)', color: '#fff' }}
              >
                {event.title}
              </button>
            ))}
            {dayEvents.length > 3 && (
              <span className="text-[10px] text-[var(--text-muted)]">+{dayEvents.length - 3} more</span>
            )}
          </div>
        </div>
      );
    }

    return cells;
  };

  const renderWeekView = () => {
    const startOfWeek = new Date(currentDate);
    startOfWeek.setDate(currentDate.getDate() - ((currentDate.getDay() - weekStartsOn + 7) % 7));

    const days: { date: Date; dateStr: string; events: CalendarEvent[] }[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(startOfWeek);
      d.setDate(startOfWeek.getDate() + i);
      const dateStr = formatDate(d.getFullYear(), d.getMonth(), d.getDate());
      days.push({ date: d, dateStr, events: eventsByDate[dateStr] || [] });
    }

    const hours = Array.from({ length: 24 }, (_, i) => i);

    return (
      <div className="flex">
        <div className="w-16 flex-shrink-0">
          <div className="h-10 border-b border-[var(--border-subtle)]" />
          {hours.map(hour => (
            <div key={hour} className="h-12 border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] text-right pr-2 pt-0.5">
              {hour.toString().padStart(2, '0')}:00
            </div>
          ))}
        </div>
        <div className="flex-1 grid grid-cols-7">
          {days.map(({ date: d, dateStr, events: dayEvents }) => {
            const isToday = dateStr === todayStr;
            return (
              <div key={dateStr} className="border-r border-[var(--border-subtle)] last:border-r-0">
                <div className={cn(
                  'h-10 flex flex-col items-center justify-center border-b border-[var(--border-subtle)]',
                  isToday && 'bg-[var(--accent)]/5'
                )}>
                  <span className="text-[10px] text-[var(--text-muted)]">{WEEKDAYS_SHORT[d.getDay()]}</span>
                  <span className={cn('text-sm font-medium', isToday ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]')}>
                    {d.getDate()}
                  </span>
                </div>
                <div className="relative">
                  {hours.map(hour => (
                    <div
                      key={hour}
                      className="h-12 border-b border-[var(--border-subtle)] hover:bg-[var(--surface-bg-hover)] cursor-pointer"
                      onClick={() => onDateClick?.(dateStr)}
                    />
                  ))}
                  {dayEvents.map(event => (
                    <button
                      key={event.id}
                      onClick={(e) => { e.stopPropagation(); onEventClick?.(event); }}
                      className="absolute left-0.5 right-0.5 text-[10px] px-1 py-0.5 rounded truncate text-white transition-opacity hover:opacity-80"
                      style={{ backgroundColor: event.color || 'var(--accent)', top: '40px' }}
                    >
                      {event.title}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className={cn('w-full border border-[var(--border-subtle)] rounded-xl bg-[var(--surface-bg)] overflow-hidden', className)}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)]">
        <div className="flex items-center gap-2">
          <button
            onClick={() => view === 'month' ? navigateMonth(-1) : navigateWeek(-1)}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-bg-hover)] text-[var(--text-secondary)] transition-colors"
            aria-label="Previous"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="text-base font-semibold text-[var(--text-primary)] min-w-[160px] text-center">
            {MONTHS[month]} {year}
          </h2>
          <button
            onClick={() => view === 'month' ? navigateMonth(1) : navigateWeek(1)}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-bg-hover)] text-[var(--text-secondary)] transition-colors"
            aria-label="Next"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
        <div className="flex items-center gap-1 bg-[var(--surface-bg-subtle)] rounded-lg p-0.5">
          {(['month', 'week'] as const).map(v => (
            <button
              key={v}
              onClick={() => handleViewChange(v)}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                currentView === v ? 'bg-[var(--surface-bg)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
              )}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {currentView === 'month' ? (
        <>
          <div className="grid grid-cols-7 border-b border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)]">
            {WEEKDAYS_SHORT.map(day => (
              <div key={day} className="py-2 text-center text-xs font-medium text-[var(--text-muted)]">
                {day}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7" role="grid">
            {renderMonthView()}
          </div>
        </>
      ) : (
        renderWeekView()
      )}
    </div>
  );
}

export { Calendar };
