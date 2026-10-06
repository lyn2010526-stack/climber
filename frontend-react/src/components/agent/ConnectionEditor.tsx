import { useId, useState } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { icons, iconSizes } from '../../lib/icons';
import { Button } from '../ui/Button';

export interface ConnectionDraft {
  url: string;
  apiKey: string;
  model: string;
}

export interface ConnectionEditorProps {
  initial?: Partial<ConnectionDraft>;
  onSubmit: (value: ConnectionDraft) => void;
  onCancel: () => void;
  className?: string;
  'data-testid'?: string;
}

const URL_PATTERN = /^https?:\/\/[^\s/$.?#].[^\s]*$/i;

const ERROR_ID = 'connection-editor-url-error';

export function isValidConnectionUrl(url: string): boolean {
  const trimmed = url.trim();
  if (!trimmed) return false;
  return URL_PATTERN.test(trimmed);
}

export function ConnectionEditor({
  initial,
  onSubmit,
  onCancel,
  className,
  'data-testid': testId = 'connection-editor',
}: ConnectionEditorProps) {
  const { t } = useI18n();
  const urlId = useId();
  const keyId = useId();
  const modelId = useId();

  const [url, setUrl] = useState(initial?.url ?? '');
  const [apiKey, setApiKey] = useState(initial?.apiKey ?? '');
  const [model, setModel] = useState(initial?.model ?? '');
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [touched, setTouched] = useState(false);

  const urlValid = isValidConnectionUrl(url);
  const showUrlError = touched && !urlValid;
  const canSubmit = urlValid && apiKey.trim().length > 0 && model.trim().length > 0;

  const copyKey = async () => {
    try {
      await navigator.clipboard?.writeText(apiKey);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const inputClasses = (invalid: boolean) =>
    cn(
      'h-[var(--control-height-md)] w-full rounded-[var(--radius-md)] border bg-[var(--color-bg-surface-2)] px-[var(--space-3)] text-[length:var(--text-sm)] text-[var(--color-text-primary)]',
      'placeholder:text-[var(--color-text-muted)]',
      'transition-colors',
      invalid
        ? 'border-[var(--color-error)] focus-visible:border-[var(--color-error)]'
        : 'border-[var(--color-border-default)] hover:border-[var(--color-border-strong)] focus-visible:border-[var(--color-border-accent)]',
      'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
    );

  return (
    <form
      data-testid={testId}
      className={cn('flex flex-col gap-[var(--space-4)]', className)}
      onSubmit={(event) => {
        event.preventDefault();
        setTouched(true);
        if (!canSubmit) return;
        onSubmit({ url: url.trim(), apiKey: apiKey.trim(), model: model.trim() });
      }}
    >
      <div className="flex flex-col gap-[var(--space-1)]">
        <label htmlFor={urlId} className="text-[length:var(--text-sm)] text-[var(--color-text-secondary)]">
          {t('agent.connection.url', { defaultValue: 'Endpoint URL' })}
        </label>
        <input
          id={urlId}
          data-testid="connection-url"
          type="text"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          value={url}
          placeholder="https://api.example.com/v1"
          aria-invalid={showUrlError}
          aria-describedby={showUrlError ? ERROR_ID : undefined}
          onBlur={() => setTouched(true)}
          onChange={(event) => setUrl(event.target.value)}
          className={inputClasses(showUrlError)}
        />
        {showUrlError && (
          <p id={ERROR_ID} role="alert" className="text-[length:var(--text-xs)] text-[var(--color-error)]">
            {t('agent.connection.url_invalid', { defaultValue: 'Enter a valid http(s) URL' })}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-[var(--space-1)]">
        <label htmlFor={keyId} className="text-[length:var(--text-sm)] text-[var(--color-text-secondary)]">
          {t('agent.connection.api_key', { defaultValue: 'API key' })}
        </label>
        <div className="relative flex items-center">
          <input
            id={keyId}
            data-testid="connection-api-key"
            type={revealed ? 'text' : 'password'}
            autoComplete="off"
            spellCheck={false}
            value={apiKey}
            placeholder="sk-..."
            onChange={(event) => setApiKey(event.target.value)}
            className={cn(inputClasses(false), 'pr-[var(--space-16)]')}
          />
          <span className="absolute right-[var(--space-2)] flex items-center gap-[var(--space-1)]">
            <button
              type="button"
              data-testid="connection-reveal"
              aria-label={
                revealed
                  ? t('agent.connection.hide_key', { defaultValue: 'Hide API key' })
                  : t('agent.connection.show_key', { defaultValue: 'Show API key' })
              }
              aria-pressed={revealed}
              onClick={() => setRevealed((value) => !value)}
              className="inline-flex size-[var(--icon-xl)] items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
            >
              {revealed ? (
                <icons.hidePassword size={iconSizes.sm} aria-hidden="true" focusable="false" />
              ) : (
                <icons.showPassword size={iconSizes.sm} aria-hidden="true" focusable="false" />
              )}
            </button>
            <button
              type="button"
              data-testid="connection-copy"
              aria-label={t('agent.connection.copy_key', { defaultValue: 'Copy API key' })}
              onClick={copyKey}
              className="inline-flex size-[var(--icon-xl)] items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
            >
              {copied ? (
                <icons.success size={iconSizes.sm} aria-hidden="true" focusable="false" />
              ) : (
                <icons.submenu size={iconSizes.sm} aria-hidden="true" focusable="false" />
              )}
            </button>
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-[var(--space-1)]">
        <label htmlFor={modelId} className="text-[length:var(--text-sm)] text-[var(--color-text-secondary)]">
          {t('agent.connection.model', { defaultValue: 'Model name' })}
        </label>
        <input
          id={modelId}
          data-testid="connection-model"
          type="text"
          autoComplete="off"
          spellCheck={false}
          value={model}
          placeholder="gpt-4o"
          onChange={(event) => setModel(event.target.value)}
          className={inputClasses(false)}
        />
      </div>

      <div className="flex items-center justify-end gap-[var(--space-2)]">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          {t('agent.connection.cancel', { defaultValue: 'Cancel' })}
        </Button>
        <Button type="submit" size="sm" disabled={!canSubmit} data-testid="connection-submit">
          {t('agent.connection.submit', { defaultValue: 'Add connection' })}
        </Button>
      </div>
    </form>
  );
}

export default ConnectionEditor;
