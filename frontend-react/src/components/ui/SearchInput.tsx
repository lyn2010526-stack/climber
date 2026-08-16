export interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  ariaLabel?: string;
}

export function SearchInput({ value, onChange, placeholder = '搜索...', className, ariaLabel = '搜索' }: SearchInputProps) {
  return (
    <div className={`relative ${className ?? ''}`}>
      <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--color-text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full pl-10 pr-4 py-2.5 rounded-2xl text-sm outline-none transition-all duration-200"
        style={{
          backgroundColor: 'var(--color-bg-surface-2)',
          border: '1px solid var(--color-border-subtle)',
          color: 'var(--color-text-primary)',
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-default)'; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-subtle)'; }}
        aria-label={ariaLabel}
      />
    </div>
  );
}
