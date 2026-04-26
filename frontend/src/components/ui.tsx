// Small, boring, reusable pieces. Kept in one file on purpose.

import { ReactNode } from "react";

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className} text-current`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="4" />
      <path
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}

export function Badge({
  tone = "slate",
  children,
}: {
  tone?: "green" | "red" | "amber" | "brand" | "slate";
  children: ReactNode;
}) {
  const palette: Record<string, string> = {
    green: "bg-green-100 text-green-700 ring-green-200",
    red: "bg-red-100 text-red-700 ring-red-200",
    amber: "bg-amber-100 text-amber-800 ring-amber-200",
    brand: "bg-brand-100 text-brand-700 ring-brand-200",
    slate: "bg-slate-100 text-slate-700 ring-slate-200",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${palette[tone]}`}
    >
      {children}
    </span>
  );
}

export function ErrorBanner({
  title,
  message,
  onDismiss,
}: {
  title: string;
  message?: string;
  onDismiss?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-md bg-red-50 border border-red-200 p-4 mb-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-red-800">{title}</h3>
          {message && <p className="mt-1 text-sm text-red-700">{message}</p>}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-red-400 hover:text-red-600 text-xs uppercase tracking-wide"
          >
            dismiss
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="text-center py-12">
      <div className="mx-auto h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
        <svg
          className="h-6 w-6 text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 9H6l-2-9m16 0H4"
          />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

export function Stat({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: ReactNode;
  tone?: "green" | "red" | "amber" | "brand" | "slate";
}) {
  const text: Record<string, string> = {
    green: "text-green-700",
    red: "text-red-700",
    amber: "text-amber-800",
    brand: "text-brand-700",
    slate: "text-slate-900",
  };
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500 font-medium">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-semibold ${text[tone]}`}>{value}</p>
    </div>
  );
}
