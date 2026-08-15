import { useToasts, type ToastVariant } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const variantClasses: Record<ToastVariant, string> = {
  default: "bg-background border",
  success: "bg-green-600 border-green-600 text-white",
  error: "bg-red-600 border-red-600 text-white",
  info: "bg-blue-600 border-blue-600 text-white",
};

export function Toaster() {
  const { toasts, dismiss } = useToasts();

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
    >
      {toasts.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => dismiss(t.id)}
          className={cn(
            "pointer-events-auto rounded-md border px-4 py-3 text-left text-sm shadow-md",
            variantClasses[t.variant]
          )}
        >
          <p className="font-medium">{t.title}</p>
          {t.description && (
            <p className={cn("mt-0.5 text-xs", t.variant === "default" ? "text-muted-foreground" : "opacity-90")}>
              {t.description}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
