import React, { useState } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
import { User } from 'lucide-react';

const avatarVariants = cva(
  'relative inline-flex items-center justify-center shrink-0 overflow-hidden bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] transition-all duration-200',
  {
    variants: {
      size: {
        sm: 'w-8 h-8 text-[10px]',
        md: 'w-10 h-10 text-xs',
        lg: 'w-12 h-12 text-sm',
        xl: 'w-16 h-16 text-lg',
      },
      shape: {
        circle: 'rounded-full',
        square: 'rounded-xl',
      },
      status: {
        none: '',
        online: '',
        offline: '',
        away: '',
        busy: '',
      },
    },
    defaultVariants: {
      size: 'md',
      shape: 'circle',
      status: 'none',
    },
  }
);

const statusIndicatorVariants = cva(
  'absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-[var(--color-bg-surface-1)]',
  {
    variants: {
      status: {
        online: 'bg-[var(--color-success)]',
        offline: 'bg-[var(--color-text-muted)]',
        away: 'bg-[var(--color-warning)]',
        busy: 'bg-[var(--color-error)]',
      },
    },
    defaultVariants: {},
  }
);

export interface AvatarProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'>, VariantProps<typeof avatarVariants> {
  src?: string;
  alt?: string;
  fallback?: React.ReactNode;
  name?: string;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0]!.charAt(0).toUpperCase();
  return (parts[0]!.charAt(0) + parts[parts.length - 1]!.charAt(0)).toUpperCase();
}

const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, size, shape, status, src, alt, fallback, name, ...props }, ref) => {
    const [imgError, setImgError] = useState(false);
    const showImage = src && !imgError;
    const initials = name ? getInitials(name) : null;

    return (
      <div ref={ref} className={cn(avatarVariants({ size, shape, status }), className)} {...props}>
        {showImage ? (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : initials ? (
          <span className="font-medium text-[var(--color-text-muted)] select-none" aria-hidden="true">{initials}</span>
        ) : fallback ? (
          <span className="flex items-center justify-center w-full h-full">{fallback}</span>
        ) : (
          <User className="w-1/2 h-1/2 text-[var(--color-text-muted)]" aria-hidden="true" />
        )}
        {status && status !== 'none' && (
          <span className={cn(statusIndicatorVariants({ status }))} aria-label={`Status: ${status}`} />
        )}
      </div>
    );
  }
);
Avatar.displayName = 'Avatar';

interface AvatarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  max?: number;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  overlap?: boolean;
}

const AvatarGroup = React.forwardRef<HTMLDivElement, AvatarGroupProps>(
  ({ className, children, max, size = 'md', overlap = true, ...props }, ref) => {
    const childArray = React.Children.toArray(children);
    const displayed = max ? childArray.slice(0, max) : childArray;
    const remaining = max ? childArray.length - max : 0;

    return (
      <div
        ref={ref}
        className={cn('flex items-center', overlap ? '-space-x-2' : 'gap-1', className)}
        role="group"
        aria-label="Avatar group"
        {...props}
      >
        {displayed.map((child, index) => (
          <div key={index} className="ring-2 ring-[var(--color-bg-surface-1)] rounded-full">
            {child}
          </div>
        ))}
        {remaining > 0 && (
          <div
            className={cn(
              'relative inline-flex items-center justify-center rounded-full bg-[var(--color-bg-surface-3)] border border-[var(--color-border-subtle)] font-medium text-[var(--color-text-muted)] ring-2 ring-[var(--color-bg-surface-1)] select-none',
              size === 'sm' && 'w-8 h-8 text-[10px]',
              size === 'md' && 'w-10 h-10 text-xs',
              size === 'lg' && 'w-12 h-12 text-sm',
              size === 'xl' && 'w-16 h-16 text-lg',
            )}
            aria-label={`+${remaining} more`}
          >
            +{remaining}
          </div>
        )}
      </div>
    );
  }
);
AvatarGroup.displayName = 'AvatarGroup';

export { Avatar, AvatarGroup, avatarVariants };
