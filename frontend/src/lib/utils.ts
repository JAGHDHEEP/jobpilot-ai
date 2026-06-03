import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function scoreColor(score: number): string {
  if (score >= 85) return "text-emerald-500";
  if (score >= 70) return "text-brand-500";
  if (score >= 50) return "text-amber-500";
  return "text-rose-500";
}

export function salaryRange(min?: number, max?: number, currency = "USD"): string {
  if (!min && !max) return "—";
  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  return fmt((min || max)!);
}
