import React from 'react';

/**
 * Accessible Button Component
 * Ensures proper ARIA attributes and keyboard support for all buttons
 */
type AccessibleButtonProps = {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  "aria-label"?: string;
  "aria-pressed"?: boolean;
  "aria-expanded"?: boolean;
  "aria-controls"?: string;
  icon?: React.ReactNode;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
};

export const AccessibleButton: React.FC<AccessibleButtonProps> = ({
  children,
  onClick,
  disabled = false,
  'aria-label': ariaLabel,
  'aria-pressed': ariaPressed,
  'aria-expanded': ariaExpanded,
  'aria-controls': ariaControls,
  icon,
  className = '',
  type = 'button',
}) => {
  // Determine if button has accessible label
  const hasAccessibleLabel =
    ariaLabel ||
    (children && typeof children === 'string' && children.trim().length > 0) ||
    (icon && false); // Icons need explicit aria-label

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-label={!hasAccessibleLabel ? undefined : (ariaLabel || children) as string}
      aria-pressed={ariaPressed}
      aria-expanded={ariaExpanded}
      aria-controls={ariaControls}
      aria-disabled={disabled ? true : undefined}
      className={className}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      {!icon && children}
    </button>
  );
};

/**
 * Icon Button with Required Accessibility Features
 * All icon buttons must have aria-label or title
 */
type IconButtonProps = {
  icon: React.ReactNode;
  "aria-label": string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  className?: string;
};

export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  'aria-label': ariaLabel,
  onClick,
  disabled = false,
  title,
  className = '',
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-disabled={disabled ? true : undefined}
      title={title}
      className={`icon-button ${className}`}
    >
      <span aria-hidden="true">{icon}</span>
    </button>
  );
};

/**
 * Submit Button
 */
type SubmitButtonProps = {
  children: React.ReactNode;
  isLoading?: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
  className?: string;
};

export const SubmitButton: React.FC<SubmitButtonProps> = ({
  children,
  isLoading = false,
  disabled,
  variant = 'primary',
  className = '',
}) => {
  return (
    <button
      type="submit"
      disabled={isLoading || disabled}
      aria-busy={isLoading ? true : undefined}
      className={`${className} btn-${variant}`}
    >
      {isLoading && (
        <span
          className="spinner"
          style={{
            display: 'inline-block',
            marginRight: '8px',
            animation: 'spin 1s linear infinite',
          }}
        />
      )}
      {children}
    </button>
  );
};
