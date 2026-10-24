import { Toaster as Sonner, toast } from "sonner";

export { toast };

export function Toaster() {
  return (
    <Sonner
      position="bottom-right"
      toastOptions={{
        style: {
          background: "var(--color-sheet)",
          color: "var(--color-ink)",
          border: "1px solid var(--color-hairline)",
          boxShadow: "var(--shadow-float)",
          fontFamily: "var(--font-sans)",
        },
      }}
    />
  );
}
