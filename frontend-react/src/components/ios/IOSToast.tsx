import { Toaster as SonnerToaster, toast } from 'sonner';

interface ToasterProps {
  position?: 'top-center' | 'top-right' | 'bottom-center' | 'bottom-right';
  theme?: 'light' | 'dark' | 'system';
}

export function IOsToaster({ position = 'top-center', theme = 'dark' }: ToasterProps) {
  return (
    <SonnerToaster
      position={position}
      theme={theme}
      toastOptions={{
        style: {
          background: 'var(--color-bg-surface-2)',
          color: 'var(--color-text-primary)',
          border: '0.5px solid var(--color-border-default)',
          borderRadius: '12px',
          fontSize: '15px',
          fontWeight: 500,
          padding: '14px 16px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
        },
        duration: 3000,
      }}
      closeButton
      richColors
    />
  );
}

export { toast };

/* ─── iOS Skeleton Loader ─── */

interface IOSSkeletonProps {
  className?: string;
  height?: number;
  width?: number | string;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
}

const radiusMap = { sm: '4px', md: '8px', lg: '12px', full: '9999px' };

export function IOSSkeleton({ className, height = 16, width = '100%', rounded = 'md' }: IOSSkeletonProps) {
  return (
    <div
      className={`ios-skeleton ${className || ''}`}
      style={{ height, width: typeof width === 'number' ? `${width}px` : width, borderRadius: radiusMap[rounded] }}
    />
  );
}

export function IOSSkeletonGroup({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={`space-y-3 ${className || ''}`}>
      {Array.from({ length: count }, (_, i) => (
        <IOSSkeleton key={i} height={20} width={i === count - 1 ? '70%' : '100%'} />
      ))}
    </div>
  );
}
