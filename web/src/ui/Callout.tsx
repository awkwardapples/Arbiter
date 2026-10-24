import { AlertTriangle, Info, OctagonAlert } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "./lib/cn";

const TONES = {
  info: { box: "border-hairline bg-sheet text-ink", icon: Info, iconClass: "text-graphite" },
  warn: { box: "border-claim/30 bg-claim-tint text-ink", icon: AlertTriangle, iconClass: "text-claim" },
  error: { box: "border-clash/30 bg-clash-tint text-ink", icon: OctagonAlert, iconClass: "text-clash" },
};

export function Callout({ tone = "info", title, children, className }: { tone?: keyof typeof TONES; title?: string; children?: ReactNode; className?: string }) {
  const t = TONES[tone];
  const Icon = t.icon;
  return (
    <div role={tone === "error" ? "alert" : "note"} className={cn("flex gap-3 rounded-panel border px-4 py-3 text-sm", t.box, className)}>
      <Icon className={cn("mt-0.5 size-4 shrink-0", t.iconClass)} aria-hidden />
      <div>
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className="text-graphite">{children}</div> : null}
      </div>
    </div>
  );
}
