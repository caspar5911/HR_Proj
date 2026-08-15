import { useSyncExternalStore } from "react";

/**
 * Lightweight, dependency-free toast system.
 *
 * `toast.success(...) / toast.error(...) / toast.info(...)` push a toast into a
 * module-level store; the `<Toaster />` component (components/ui/toaster.tsx)
 * subscribes via `useToasts()` and renders them. Toasts auto-dismiss.
 */

export type ToastVariant = "default" | "success" | "error" | "info";

export interface ToastItem {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

const AUTO_DISMISS_MS = 4000;

let toasts: ToastItem[] = [];
let listeners: Array<() => void> = [];
let nextId = 1;

function emit() {
  for (const l of listeners) l();
}

function subscribe(listener: () => void) {
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

function getSnapshot() {
  return toasts;
}

export function pushToast(input: {
  title: string;
  description?: string;
  variant?: ToastVariant;
}): number {
  const id = nextId++;
  toasts = [...toasts, { id, variant: "default", ...input }];
  emit();
  if (AUTO_DISMISS_MS > 0) {
    setTimeout(() => dismissToast(id), AUTO_DISMISS_MS);
  }
  return id;
}

export function dismissToast(id: number) {
  if (!toasts.some((t) => t.id === id)) return;
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

/** Test helper — reads the current toast list without a React render. */
export function getToasts(): ToastItem[] {
  return toasts;
}

/** Test helper — clears all toasts. */
export function clearToasts() {
  toasts = [];
  emit();
}

export const toast = {
  success: (title: string, description?: string) =>
    pushToast({ title, description, variant: "success" }),
  error: (title: string, description?: string) =>
    pushToast({ title, description, variant: "error" }),
  info: (title: string, description?: string) =>
    pushToast({ title, description, variant: "info" }),
};

export function useToasts() {
  const items = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  return { toasts: items, dismiss: dismissToast };
}
