import type { ButtonHTMLAttributes } from "react";
import "./Button.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  fullWidth?: boolean;
};

export function Button({
  variant = "primary",
  fullWidth,
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <button
      type="button"
      className={`nl-btn nl-btn--${variant} ${fullWidth ? "nl-btn--full" : ""} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  );
}
