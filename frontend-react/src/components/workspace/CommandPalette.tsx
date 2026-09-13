import { useState, useEffect, useRef, useMemo } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { ALL_NAV_ITEMS_BASE } from '../../navigation/navConfig';
import { useI18n } from '../../i18n';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
}

export default function CommandPalette({ isOpen, onClose, onNavigate }: CommandPaletteProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const keyboardIndexRef = useRef(0);

  const allItems = useMemo(() => ALL_NAV_ITEMS_BASE
    .filter(item => item.id !== 'demo')
    .map(item => ({
      id: item.id,
      label: t(item.labelKey ?? item.label ?? item.id),
      icon: item.icon,
      keywords: item.keywords ?? '',
      group: t(`nav_groups.${item.group ?? 'config'}`),
    })), [t]);

  const filtered = useMemo(() => {
    if (!query.trim()) return allItems.slice(0, 8);
    const q = query.toLowerCase();
    return allItems.filter(item =>
      item.label.toLowerCase().includes(q) ||
      item.keywords.toLowerCase().includes(q) ||
      item.group.toLowerCase().includes(q)
    );
  }, [query, allItems]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => {
          keyboardIndexRef.current = Math.min(i + 1, filtered.length - 1);
          return keyboardIndexRef.current;
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => {
          keyboardIndexRef.current = Math.max(i - 1, 0);
          return keyboardIndexRef.current;
        });
      } else if (e.key === 'Enter' && filtered[selectedIndex]) {
        onNavigate(filtered[selectedIndex].id);
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose, onNavigate]);

  if (!isOpen) return null;

  const grouped = filtered.reduce<Record<string, typeof allItems>>((acc, item) => {
    if (!acc[item.group]) acc[item.group] = [];
    (acc[item.group] ||= []).push(item);
    return acc;
  }, {});

  return (
        <div className="fixed inset-0 z-[100]" onClick={onClose} role="dialog" aria-modal="true" aria-label={t('common.command_palette')}>
      <div className="absolute inset-0" style={{ backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }} />
      <div
        className="relative mx-auto mt-[20vh] w-full max-w-[640px] max-h-[480px] flex flex-col rounded-2xl overflow-hidden"
        style={{
          backgroundColor: 'var(--color-bg-surface-1)',
          border: '1px solid var(--color-border-default)',
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
          <Search size={18} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`${t('common.search')}...`}
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: 'var(--color-text-primary)' }}
          />
          <kbd className="text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
            backgroundColor: 'var(--color-bg-surface-3)',
            color: 'var(--color-text-muted)',
            border: '1px solid var(--color-border-subtle)'
          }}>ESC</kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="flex-1 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="py-12 text-center" style={{ color: 'var(--color-text-muted)' }}>
              <Search size={32} className="mx-auto mb-3 opacity-50" />
              <p className="text-sm">{t('common.no_results')} "{query}"</p>
            </div>
          ) : (
            Object.entries(grouped).map(([group, items]) => (
              <div key={group} className="mb-2">
                {filtered.length > 3 && (
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{
                    color: 'var(--color-text-muted)'
                  }}>
                    {group}
                  </div>
                )}
                <div className="space-y-0.5">
                  {items.map((item) => {
                    const globalIndex = filtered.indexOf(item);
                    const IconComponent = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => { onNavigate(item.id); onClose(); }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm text-left transition-all duration-150"
                        style={{
                          backgroundColor: globalIndex === selectedIndex ? 'var(--color-bg-surface-2)' : 'transparent',
                          color: globalIndex === selectedIndex ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                        }}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                        onMouseLeave={() => setSelectedIndex(keyboardIndexRef.current)}
                      >
                        <div className="p-1.5 rounded-lg" style={{
                          backgroundColor: globalIndex === selectedIndex ? 'var(--color-accent-subtle)' : 'var(--color-bg-surface-3)',
                          color: globalIndex === selectedIndex ? 'var(--color-accent)' : 'var(--color-text-muted)',
                        }}>
                          <IconComponent size={14} />
                        </div>
                        <span className="flex-1">{item.label}</span>
                        {globalIndex === selectedIndex && (
                          <ArrowRight size={14} style={{ color: 'var(--color-accent)' }} />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2 flex items-center gap-4 text-[10px]" style={{
          borderTop: '1px solid var(--color-border-subtle)',
          color: 'var(--color-text-muted)',
          backgroundColor: 'var(--color-bg-surface-2)',
        }}>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded font-mono" style={{ border: '1px solid var(--color-border-subtle)' }}>↑↓</kbd> {t('common.navigate')}
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded font-mono" style={{ border: '1px solid var(--color-border-subtle)' }}>↵</kbd> {t('common.open')}
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded font-mono" style={{ border: '1px solid var(--color-border-subtle)' }}>esc</kbd> {t('common.close')}
          </span>
        </div>
      </div>
    </div>
  );
}
