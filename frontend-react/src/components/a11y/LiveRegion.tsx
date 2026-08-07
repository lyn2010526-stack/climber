import React, { useEffect, useRef } from 'react';

/**
 * Live Region for Accessibility Announcements
 * Provides screen reader announcements for dynamic content updates
 */

type LiveRegionProps = {
  children: React.ReactNode;
  ariaLive?: 'polite' | 'assertive' | 'off';
  className?: string;
};

export const LiveRegion: React.FC<LiveRegionProps> = ({
  children,
  ariaLive = 'polite',
  className = '',
}) => {
  return (
    <div
      role="status"
      aria-live={ariaLive}
      aria-atomic="true"
      className={`live-region ${className}`}
    >
      {children}
    </div>
  );
};

/**
 * Hook for making accessibility announcements
 */
export const useAccessibilityAnnouncer = () => {
  const [announcement, setAnnouncement] = React.useState<string>('');
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const announce = React.useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setAnnouncement(message);

    // Clear the announcement after a delay to allow screen readers to read it
    timeoutRef.current = setTimeout(() => {
      setAnnouncement('');
    }, 5000);
  }, []);

  return { announcement, announce };
};

/**
 * Component for announcing messages via screen readers
 */
export const AnnounceMessage: React.FC<{ message: string | null }> = ({ message }) => {
  return <LiveRegion ariaLive="assertive">{message}</LiveRegion>;
};
