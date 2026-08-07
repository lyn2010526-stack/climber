import React from 'react';

/**
 * Accessible Form Field Components
 */

type LabelProps = {
  children: React.ReactNode;
  htmlFor?: string;
  required?: boolean;
  className?: string;
};

export const Label: React.FC<LabelProps> = ({
  children,
  htmlFor,
  required = false,
  className = '',
}) => {
  return (
    <label
      htmlFor={htmlFor}
      className={`form-label ${required ? 'form-label-required' : ''} ${className}`}
    >
      {children}
      {required && <span className="sr-only">required</span>}
    </label>
  );
};

type InputBaseProps = {
  id?: string;
  name: string;
  type?: string;
  label?: string;
  placeholder?: string;
  value?: string | number;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur?: () => void;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  className?: string;
  autoComplete?: string;
};

export const Input: React.FC<InputBaseProps> = ({
  id,
  name,
  type = 'text',
  label,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  required = false,
  disabled = false,
  'aria-describedby': ariaDescribedBy,
  'aria-invalid': ariaInvalid,
  className = '',
  autoComplete,
}) => {
  const inputId = id || name;
  const describedBy = [error ? `${inputId}-error` : undefined, ariaDescribedBy]
    .filter(Boolean)
    .join(' ') || undefined;

  return (
    <div className="form-field">
      {label && (
        <Label htmlFor={inputId} required={required}>
          {label}
        </Label>
      )}
      <input
        id={inputId}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        required={required}
        disabled={disabled}
        aria-describedby={describedBy}
        aria-invalid={ariaInvalid || !!error}
        aria-errormessage={error ? `${inputId}-error` : undefined}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className={`form-input ${className}`}
      />
      {error && (
        <p id={`${inputId}-error`} className="form-error-message" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

type TextAreaProps = {
  id?: string;
  name: string;
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onBlur?: () => void;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  rows?: number;
  className?: string;
};

export const TextArea: React.FC<TextAreaProps> = ({
  id,
  name,
  label,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  required = false,
  disabled = false,
  rows = 4,
  className = '',
}) => {
  const textareaId = id || name;
  const describedBy = error ? `${textareaId}-error` : undefined;

  return (
    <div className="form-field">
      {label && (
        <Label htmlFor={textareaId} required={required}>
          {label}
        </Label>
      )}
      <textarea
        id={textareaId}
        name={name}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        required={required}
        disabled={disabled}
        aria-describedby={describedBy}
        aria-invalid={!!error}
        aria-errormessage={error ? `${textareaId}-error` : undefined}
        placeholder={placeholder}
        rows={rows}
        className={`form-input ${className}`}
      />
      {error && (
        <p id={`${textareaId}-error`} className="form-error-message" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

type SelectProps = {
  id?: string;
  name: string;
  label?: string;
  options: SelectOption[];
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onBlur?: () => void;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
};

export const Select: React.FC<SelectProps> = ({
  id,
  name,
  label,
  options,
  value,
  onChange,
  onBlur,
  error,
  required = false,
  disabled = false,
  placeholder,
  className = '',
}) => {
  const selectId = id || name;
  const describedBy = error ? `${selectId}-error` : undefined;

  return (
    <div className="form-field">
      {label && (
        <Label htmlFor={selectId} required={required}>
          {label}
        </Label>
      )}
      <select
        id={selectId}
        name={name}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        required={required}
        disabled={disabled}
        aria-describedby={describedBy}
        aria-invalid={!!error}
        aria-errormessage={error ? `${selectId}-error` : undefined}
        className={`form-input ${className}`}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={`${selectId}-error`} className="form-error-message" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

type CheckboxProps = {
  id?: string;
  name: string;
  label?: string;
  checked?: boolean;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
};

export const Checkbox: React.FC<CheckboxProps> = ({
  id,
  name,
  label,
  checked = false,
  onChange,
  error,
  required = false,
  disabled = false,
  className = '',
}) => {
  const checkboxId = id || name;
  const describedBy = error ? `${checkboxId}-error` : undefined;

  return (
    <div className="form-field form-field-checkbox">
      <div className="form-checkbox-wrapper">
        <input
          id={checkboxId}
          name={name}
          type="checkbox"
          checked={checked}
          onChange={onChange}
          required={required}
          disabled={disabled}
          aria-describedby={describedBy}
          aria-invalid={!!error}
          className={`form-checkbox ${className}`}
        />
        {label && (
          <Label htmlFor={checkboxId} className="form-checkbox-label">
            {label}
            {required && <span className="sr-only">required</span>}
          </Label>
        )}
      </div>
      {error && (
        <p id={`${checkboxId}-error`} className="form-error-message" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

type RadioOption = {
  value: string;
  label: string;
};

type RadioGroupProps = {
  id?: string;
  name: string;
  label?: string;
  options: RadioOption[];
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  orientation?: 'horizontal' | 'vertical';
  className?: string;
};

export const RadioGroup: React.FC<RadioGroupProps> = ({
  id,
  name,
  label,
  options,
  value,
  onChange,
  error,
  required = false,
  disabled = false,
  orientation = 'vertical',
  className = '',
}) => {
  const radioGroupId = id || name;
  const describedBy = error ? `${radioGroupId}-error` : undefined;

  return (
    <div className="form-field">
      {label && (
        <fieldset className="form-fieldset">
          <legend className="form-legend">
            <Label htmlFor={radioGroupId} required={required}>
              {label}
            </Label>
          </legend>
          <div
            className={`form-radio-group ${orientation === 'horizontal' ? 'form-radio-horizontal' : ''}`}
            role="radiogroup"
            aria-labelledby={radioGroupId}
            aria-describedby={describedBy}
            aria-invalid={!!error}
          >
            {options.map((option) => (
              <label key={option.value} className="form-radio-label">
                <input
                  type="radio"
                  name={name}
                  value={option.value}
                  checked={value === option.value}
                  onChange={onChange}
                  disabled={disabled}
                  className="form-radio"
                />
                <span className="form-radio-text">{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {error && (
        <p id={`${radioGroupId}-error`} className="form-error-message" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};
