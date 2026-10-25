import { type ReactElement, type ReactNode, cloneElement, useId } from "react";
import { cn } from "./lib/cn";

interface ControlProps {
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

/** A labelled form control. The error sits under its own field and is announced with it. */
export function Field({
  label,
  hint,
  error,
  children,
  className,
  name,
}: {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  children: ReactElement<ControlProps>;
  className?: string;
  /** Test hook: `field-<name>` on the wrapper and `error-<name>` on the message. */
  name?: string;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const control = cloneElement(children, {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": [hintId, errorId].filter(Boolean).join(" ") || undefined,
  });
  return (
    <div className={cn("flex flex-col gap-1", className)} data-testid={name ? `field-${name}` : undefined}>
      <label htmlFor={id} className="text-xs font-semibold text-ink">
        {label}
      </label>
      {control}
      {hint ? (
        <p id={hintId} className="text-xs text-graphite">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-xs text-clash" data-testid={name ? `error-${name}` : undefined}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** A group of controls under one legend (chips, radio-like buttons), with its error. */
export function FieldGroup({
  legend,
  error,
  children,
  name,
  className,
}: {
  legend: ReactNode;
  error?: string;
  children: ReactNode;
  name?: string;
  className?: string;
}) {
  return (
    <fieldset className={cn("flex flex-col gap-1", className)} data-testid={name ? `field-${name}` : undefined}>
      <legend className="mb-1 text-xs font-semibold text-ink">{legend}</legend>
      {children}
      {error ? (
        <p role="alert" className="text-xs text-clash" data-testid={name ? `error-${name}` : undefined}>
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
