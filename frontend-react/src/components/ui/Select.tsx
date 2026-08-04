import { useState, useRef, useEffect, forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import { ChevronDown, Check, X } from 'lucide-react';
import { cn } from '../../lib/utils';

const selectVariants = cva(
  'flex w-full items-center justify-between rounded-lg border bg-white/[0.03] px-3 py-2 text-sm transition-all duration-200 text-white cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50',
  {
    variants: {
      variant: {
        default: 'border-white/[0.08] hover:border-white/[0.12]',
        error: 'border-red-500/50',
        success: 'border-emerald-500/50',
      },
      inputSize: {
        sm: 'h-8 px-2.5 text-xs',
        md: 'h-10 px-3 text-sm',
        lg: 'h-12 px-4 text-base',
      },
    },
    defaultVariants: {
      variant: 'default',
      inputSize: 'md',
    },
  }
);

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
  icon?: React.ReactNode;
}

interface SelectProps {
  value?: string;
  onChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  searchable?: boolean;
  clearable?: boolean;
  multiple?: boolean;
  className?: string;
  variant?: 'default' | 'error' | 'success';
  inputSize?: 'sm' | 'md' | 'lg';
  maxHeight?: number;
}

const Select = forwardRef<HTMLDivElement, SelectProps>(
  ({ value, onChange, options, placeholder = '请选择', disabled, searchable, clearable, multiple, className, variant, inputSize, maxHeight = 240 }, ref) => {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const containerRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    const selectedValues = multiple && value ? value.split(',') : value ? [value] : [];

    const filteredOptions = searchable && search
      ? options.filter((opt) => opt.label.toLowerCase().includes(search.toLowerCase()))
      : options;

    useEffect(() => {
      function handleClickOutside(e: MouseEvent) {
        if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
          setIsOpen(false);
          setSearch('');
        }
      }
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
      if (isOpen && searchable && searchInputRef.current) {
        searchInputRef.current.focus();
      }
    }, [isOpen, searchable]);

    useEffect(() => {
      setHighlightedIndex(-1);
    }, [search]);

    const toggleOption = (optionValue: string) => {
      if (multiple) {
        const current = value ? value.split(',') : [];
        const updated = current.includes(optionValue)
          ? current.filter((v) => v !== optionValue)
          : [...current, optionValue];
        onChange?.(updated.join(','));
      } else {
        onChange?.(optionValue);
        setIsOpen(false);
        setSearch('');
      }
    };

    const handleClear = (e: React.MouseEvent) => {
      e.stopPropagation();
      onChange?.('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (!isOpen) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setIsOpen(true);
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) => (prev < filteredOptions.length - 1 ? prev + 1 : 0));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : filteredOptions.length - 1));
          break;
        case 'Enter':
          e.preventDefault();
          if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
            toggleOption(filteredOptions[highlightedIndex].value);
          }
          break;
        case 'Escape':
          setIsOpen(false);
          setSearch('');
          break;
      }
    };

    const getSelectedLabels = () => {
      return selectedValues
        .map((v) => options.find((opt) => opt.value === v)?.label)
        .filter(Boolean)
        .join(', ');
    };

    return (
      <div ref={containerRef} className={cn('relative w-full', className)}>
        <div
          ref={ref}
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          tabIndex={disabled ? -1 : 0}
          onClick={() => !disabled && setIsOpen(!isOpen)}
          onKeyDown={handleKeyDown}
          className={cn(
            selectVariants({ variant, inputSize }),
            disabled && 'opacity-50 cursor-not-allowed',
            isOpen && 'ring-2 ring-blue-500/50 border-blue-500/50',
          )}
        >
          <span className={cn('flex-1 truncate text-left', !value && 'text-white/40')}>
            {multiple && value
              ? (selectedValues.length > 0 && (
                  <span className="flex items-center gap-1.5">
                    {selectedValues.slice(0, 2).map((v) => {
                      const opt = options.find((o) => o.value === v);
                      return (
                        <span key={v} className="inline-flex items-center gap-1 rounded-md bg-white/[0.08] px-1.5 py-0.5 text-xs">
                          {opt?.label}
                        </span>
                      );
                    })}
                    {selectedValues.length > 2 && (
                      <span className="text-white/40 text-xs">+{selectedValues.length - 2}</span>
                    )}
                  </span>
                )) || placeholder
              : getSelectedLabels() || placeholder}
          </span>
          <div className="flex items-center gap-1 ml-2">
            {clearable && value && (
              <button
                type="button"
                onClick={handleClear}
                className="p-0.5 rounded hover:bg-white/10 text-white/30 hover:text-white/60"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            <ChevronDown className={cn('h-4 w-4 text-white/40 transition-transform duration-200', isOpen && 'rotate-180')} />
          </div>
        </div>

        {isOpen && (
          <div
            className="absolute z-50 mt-1 w-full rounded-xl border border-white/[0.08] bg-[#1a1a2e] shadow-xl shadow-black/40 overflow-hidden animate-in fade-in slide-in-from-top-1 duration-150"
            role="listbox"
            style={{ maxHeight }}
          >
            {searchable && (
              <div className="p-2 border-b border-white/[0.06]">
                <input
                  ref={searchInputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="搜索..."
                  className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-sm text-white placeholder:text-white/30 outline-none focus:ring-1 focus:ring-blue-500/30"
                />
              </div>
            )}
            <div className="overflow-y-auto" style={{ maxHeight: maxHeight - (searchable ? 52 : 0) }}>
              {filteredOptions.length === 0 ? (
                <div className="px-3 py-6 text-center text-sm text-white/30">
                  无匹配选项
                </div>
              ) : (
                filteredOptions.map((option, index) => {
                  const isSelected = selectedValues.includes(option.value);
                  return (
                    <div
                      key={option.value}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => !option.disabled && toggleOption(option.value)}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 text-sm transition-colors cursor-pointer',
                        isSelected && 'bg-blue-500/10 text-blue-400',
                        !isSelected && 'text-white/70 hover:bg-white/[0.04] hover:text-white',
                        option.disabled && 'opacity-30 cursor-not-allowed',
                        index === highlightedIndex && !isSelected && 'bg-white/[0.04]',
                      )}
                    >
                      {option.icon && <span className="shrink-0">{option.icon}</span>}
                      <span className="flex-1 truncate">{option.label}</span>
                      {isSelected && <Check className="h-4 w-4 shrink-0" />}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    );
  }
);
Select.displayName = 'Select';

export { Select, selectVariants };
export type { SelectProps, SelectOption };
