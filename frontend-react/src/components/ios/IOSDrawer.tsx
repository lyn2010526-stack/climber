import { Drawer } from 'vaul';
import { cn } from '../../lib/utils';
import type { ReactNode } from 'react';

interface IOSDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function IOSDrawer({ open, onOpenChange, title, children, className }: IOSDrawerProps) {
  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange} shouldScaleBackground>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50" />
        <Drawer.Content
          className={cn(
            'fixed bottom-0 left-0 right-0 z-50 flex flex-col rounded-t-[12px] bg-[var(--color-bg-surface-1)] border-t border-[var(--color-border-subtle)] outline-none',
            className
          )}
        >
          <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-[var(--color-bg-surface-3)]" />
          {title && (
            <div className="flex items-center justify-center px-4 py-3 border-b border-[var(--color-border-subtle)]">
              <Drawer.Title className="ios-headline text-[var(--color-text-primary)]">{title}</Drawer.Title>
            </div>
          )}
          <div className="flex-1 overflow-y-auto p-4">{children}</div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
