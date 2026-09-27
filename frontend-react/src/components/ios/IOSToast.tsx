import { Toaster as SonnerToaster, toast } from 'sonner';

interface ToasterProps {
  position?: 'top-center' | 'top-right' | 'bottom-center' | 'bottom-right';
  theme?: 'light' | 'dark' | 'system';
}

export function IOsToaster({ position = 'top-center', theme = 'system' }: ToasterProps) {
  return (
    <SonnerToaster
      position={position}
      theme={theme}
      toastOptions={{
        style: {
          background: 'var(--color-bg-surface-2)',
          color: 'var(--color-text-primary)',
          border: '0.5px solid var(--color-border-default)',
          borderRadius: 'var(--radius-lg)',
          fontSize: 'var(--text-sm)',
          fontWeight: 500,
          padding: 'var(--space-3) var(--space-4)',
          boxShadow: 'var(--shadow-lg)',
        },
        duration: 3000,
      }}
      closeButton
      richColors
    />
  );
}

export { toast };
