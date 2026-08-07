import { useState, useRef, useEffect, ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { ChevronDown, Search, X, Check, AlertCircle } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
  description?: string;
}

export interface SelectOptionGroup {
  label: string;
  options: SelectOption[];
}

interface SelectBaseProps {
  size?: 'sm' | 'md' | 'lg';
  error?: string;
  hint?: string;
  placeholder?: string;
  leftIcon?: ReactNode;
  searchable?: boolean;
  clearable?: boolean;
  disabled?: boolean;
  className?: string;
}

interface SingleSelectProps extends SelectBaseProps {
  multiple?: false;
  options?: SelectOption[];
  groups?: SelectOptionGroup[];
  value?: string;
  onChange: (value: string) => void;
}

interface MultipleSelectProps extends SelectBaseProps {
  multiple: true;
  options?: SelectOption[];
  groups?: SelectOptionGroup[];
  value?: string[];
  onChange: (value: string[]) => void;
}

export type SelectProps = SingleSelectProps | MultipleSelectProps;

export function Select(props: SelectProps) {
  const {
    size = 'md', error, hint, placeholder = '请选择...', leftIcon, searchable = false,
    clearable = false, disabled = false, className, multiple = false, options = [], groups,
    value, onChange,
  } = props;

  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchText('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && searchable && inputRef.current) inputRef.current.focus();
  }, [isOpen, searchable]);

  const getSelectedValues = (): string[] => {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  };

  const allOptions: SelectOption[] = groups
    ? groups.flatMap(group => group.options)
    : options;

  const filteredOptions = searchText
    ? allOptions.filter(opt => opt.label.toLowerCase().includes(searchText.toLowerCase()))
    : allOptions;

  const getFilteredGroups = (): SelectOptionGroup[] => {
    if (!groups) return [];
    return groups.map(group => ({
      label: group.label,
      options: group.options.filter(opt => opt.label.toLowerCase().includes(searchText.toLowerCase())),
    })).filter(group => group.options.length > 0);
  };

  const selectedValues = getSelectedValues();
  const displayValue = selectedValues.length > 0
    ? selectedValues.map(v => allOptions.find(o => o.value === v)?.label).filter(Boolean).join(', ')
    : '';

  const handleSelect = (optionValue: string) => {
    if (multiple) {
      const current = Array.isArray(value) ? value : [];
      const next = current.includes(optionValue)
        ? current.filter(v => v !== optionValue)
        : [...current, optionValue];
      (onChange as (value: string[]) => void)(next);
    } else {
      (onChange as (value: string) => void)(optionValue);
      setIsOpen(false);
      setSearchText('');
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    multiple ? (onChange as (value: string[]) => void)([]) : (onChange as (value: string) => void)('');
    setSearchText('');
  };

  const sizeMap = { sm: 'h-8 text-xs px-3 rounded-lg', md: 'h-10 text-sm px-3.5 rounded-xl', lg: 'h-11 text-sm px-4 rounded-xl' };
  const iconSizeMap = { sm: 12, md: 14, lg: 16 };

  const renderOption = (option: SelectOption) => {
    const isSelected = selectedValues.includes(option.value);
    return (
      <div
        key={option.value}
        className={cn(
          'flex items-center gap-2.5 px-3 py-2 cursor-pointer rounded-lg mx-1 transition-colors',
          isSelected ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]' : 'hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)]',
          option.disabled && 'opacity-40 cursor-not-allowed'
        )}
        onClick={() => !option.disabled && handleSelect(option.value)}
      >
        {multiple && (
          <div className={cn('w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0',
            isSelected ? 'bg-[var(--color-accent)] border-[var(--color-accent)]' : 'border-[var(--color-border-default)]'
          )}>
            {isSelected && <Check size={10} className="text-white" />}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="text-sm leading-tight">{option.label}</div>
          {option.description && <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{option.description}</div>}
        </div>
        {!multiple && isSelected && <Check size={iconSizeMap[size]} className="text-[var(--color-accent)] shrink-0" />}
      </div>
    );
  };

  return (
    <div className="w-full" ref={containerRef}>
      <div
        className={cn(
          'relative flex items-center border bg-[var(--color-bg-surface-1)] cursor-pointer',
          'transition-all duration-150',
          sizeMap[size],
          !disabled && 'hover:border-[var(--color-border-strong)]',
          isOpen && !disabled && 'ring-2 ring-[var(--color-accent)]/20 border-[var(--color-accent)]',
          error && 'border-[var(--color-error)]',
          !error && !isOpen && 'border-[var(--color-border-default)]',
          disabled && 'opacity-50 cursor-not-allowed bg-[var(--color-bg-surface-2)]',
          className
        )}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        {leftIcon && <span className="mr-2 flex items-center text-[var(--color-text-muted)]">{leftIcon}</span>}
        <span className={cn('flex-1 truncate', !displayValue && 'text-[var(--color-text-muted)]')}>
          {displayValue || placeholder}
        </span>
        <span className="flex items-center gap-1 ml-2 shrink-0">
          {clearable && displayValue && (
            <button onClick={handleClear} className="p-0.5 rounded hover:bg-[var(--color-bg-surface-3)] text-[var(--color-text-muted)]">
              <X size={iconSizeMap[size]} />
            </button>
          )}
          <ChevronDown size={iconSizeMap[size]} className={cn('text-[var(--color-text-muted)] transition-transform duration-200', isOpen && 'rotate-180')} />
        </span>
      </div>

      {isOpen && !disabled && (
        <div className="absolute z-50 mt-1.5 w-full min-w-[200px] rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1)] animate-[fadeIn_150ms_ease-out]">
          {searchable && (
            <div className="p-2 border-b border-[var(--color-border-subtle)]">
              <div className="flex items-center gap-2 px-2">
                <Search size={12} className="text-[var(--color-text-muted)] shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={searchText}
                  onChange={e => setSearchText(e.target.value)}
                  placeholder="搜索..."
                  className="w-full bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none"
                />
              </div>
            </div>
          )}
          <div className="max-h-60 overflow-y-auto py-1">
            {groups ? getFilteredGroups().map(group => (
              <div key={group.label}>
                <div className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{group.label}</div>
                {group.options.map(renderOption)}
              </div>
            )) : filteredOptions.map(renderOption)}
            {filteredOptions.length === 0 && (
              <div className="px-3 py-6 text-center text-sm text-[var(--color-text-muted)]">无匹配结果</div>
            )}
          </div>
        </div>
      )}

      {error && <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1"><AlertCircle size={10} />{error}</p>}
      {hint && !error && <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">{hint}</p>}
    </div>
  );
}
