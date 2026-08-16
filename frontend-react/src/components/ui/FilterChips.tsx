export interface FilterChipsProps {
  options: Array<{ value: string; label: string }>;
  selected: string;
  onChange: (value: string) => void;
  className?: string;
}

export function FilterChips({ options, selected, onChange, className }: FilterChipsProps) {
  return (
    <div className={`flex flex-wrap gap-2 ${className ?? ''}`}>
      {options.map(option => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className="px-4 py-2 rounded-2xl text-xs font-semibold transition-all duration-200 border"
          style={selected === option.value
            ? { backgroundColor: 'var(--color-accent-subtle)', borderColor: 'var(--color-border-accent)', color: 'var(--color-text-primary)' }
            : { backgroundColor: 'transparent', borderColor: 'var(--color-border-subtle)', color: 'var(--color-text-muted)' }
          }
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
