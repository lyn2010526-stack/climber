import React, { useEffect } from 'react';

/**
 * Skip to Main Content Link
 * Enables keyboard users to skip navigation and go directly to main content
 */
export const SkipToMain: React.FC = () => {
  return (
    <a href="#main-content" className="skip-link">
      Skip to main content
    </a>
  );
};

/**
 * Handle Skip Link Focus
 * Ensure the main content area is focusable when skipped to
 */
export const useSkipToMain = (): React.RefObject<HTMLDivElement> => {
  const mainRef = React.useRef<HTMLDivElement>(null!);

  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#main-content' && mainRef.current) {
        mainRef.current.focus();
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return mainRef;
};
