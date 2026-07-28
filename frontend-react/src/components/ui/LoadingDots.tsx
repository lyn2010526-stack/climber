import React from 'react';
import { cn } from '../../lib/utils';

/* Reference: Lobe UI `chat/LoadingDots/LoadingDots.tsx` */
interface LoadingDotsProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = {
  sm: 'w-1 h-1',
  md: 'w-1.5 h-1.5',
  lg: 'w-2 h-2',
};

export const LoadingDots: React.FC<LoadingDotsProps> = ({
  className,
  size = 'md',
}) => {
  return (
    <div className={cn('flex items-center gap-1', className)}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={cn(
            'rounded-full bg-current animate-loading-dots',
            sizeMap[size]
          )}
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  );
};

export default LoadingDots;
