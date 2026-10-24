import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { cn } from "./lib/cn";

/** A real identifier (run, case, request, receipt id or hash) in mono, copyable. */
export function Identifier({ value, short, className }: { value: string; short?: number; className?: string }) {
  const [copied, setCopied] = useState(false);
  const shown = short && value.length > short ? `${value.slice(0, short)}…` : value;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      title={copied ? "Copied" : `Copy ${value}`}
      className={cn("inline-flex items-center gap-1 rounded-[4px] font-mono text-xs text-graphite hover:bg-well hover:text-ink", className)}
    >
      <span>{shown}</span>
      {copied ? <Check className="size-3" aria-hidden /> : <Copy className="size-3 opacity-60" aria-hidden />}
      <span className="sr-only">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}
