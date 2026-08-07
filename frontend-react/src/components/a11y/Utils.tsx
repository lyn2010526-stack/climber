import React from 'react';

/**
 * Accessibility Utilities
 */

// Screen Reader Only Text - hides content visually but makes it available to screen readers
type ScreenReaderTextProps = {
  children: React.ReactNode;
};

export const ScreenReaderText: React.FC<ScreenReaderTextProps> = ({ children }) => {
  return (
    <span className="sr-only">
      {children}
    </span>
  );
};

/**
 * Skip Link Component
 */
type SkipLinkProps = {
  targetId: string;
  text?: string;
};

export const SkipLink: React.FC<SkipLinkProps> = ({ targetId, text = 'Skip to main content' }) => {
  return (
    <a
      href={`#${targetId}`}
      className="skip-link"
      tabIndex={0}
    >
      {text}
    </a>
  );
};

/**
 * Button with Icon and Label
 * Best practice: Always provide both icon and aria-label for icon buttons
 */
type IconButtonWithLabelProps = {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  "aria-expanded"?: boolean;
  "aria-pressed"?: boolean;
  "aria-controls"?: string;
  variant?: 'default' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
};

export const IconButtonWithLabel: React.FC<IconButtonWithLabelProps> = ({
  icon,
  label,
  onClick,
  disabled = false,
  'aria-expanded': ariaExpanded,
  'aria-pressed': ariaPressed,
  'aria-controls': ariaControls,
  variant = 'default',
  size = 'md',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'p-2 text-sm',
    md: 'p-3 text-base',
    lg: 'p-4 text-lg',
  };

  const variantClasses = {
    default: '',
    ghost: 'hover:bg-opacity-10',
    outline: 'border border-border-default hover:border-border-strong',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-expanded={ariaExpanded}
      aria-pressed={ariaPressed}
      aria-controls={ariaControls}
      aria-disabled={disabled ? true : undefined}
      className={`icon-button ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
    >
      <span aria-hidden="true">{icon}</span>
      <ScreenReaderText>{label}</ScreenReaderText>
    </button>
  );
};

/**
 * Heading with Semantic Structure
 * Ensures proper heading hierarchy
 */
type AccessibleHeadingProps = {
  level?: 1 | 2 | 3 | 4 | 5 | 6;
  children: React.ReactNode;
  className?: string;
  id?: string;
};

export const AccessibleHeading: React.FC<AccessibleHeadingProps> = ({
  level = 2,
  children,
  className = '',
  id,
}) => {
  const Tag = `h${level}` as 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
  
  const headingStyles = {
    1: 'text-3xl font-bold',
    2: 'text-2xl font-bold',
    3: 'text-xl font-semibold',
    4: 'text-lg font-medium',
    5: 'text-base font-medium',
    6: 'text-sm font-medium',
  };

  return (
    <Tag id={id} className={`${headingStyles[level]} ${className}`}>
      {children}
    </Tag>
  );
};
