import type { InputHTMLAttributes } from "react";
import "./Input.css";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
};

export function Input({ label, error, id, className = "", ...rest }: Props) {
  const inputId = id ?? label.replace(/\s+/g, "-").toLowerCase();
  return (
    <label className={`nl-field ${className}`.trim()} htmlFor={inputId}>
      <span className="nl-field__label">{label}</span>
      <input id={inputId} className={`nl-field__input ${error ? "nl-field__input--error" : ""}`} {...rest} />
      {error ? <span className="nl-field__error">{error}</span> : null}
    </label>
  );
}
