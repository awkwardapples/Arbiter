import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";

export const REPO_BLOB = "https://github.com/awkwardapples/Arbiter/blob/main";

/** A link to a committed document on GitHub, opened in a new tab. */
export function DocLink({ path, anchor, children }: { path: string; anchor?: string; children?: ReactNode }) {
  const href = `${REPO_BLOB}/${path}${anchor ? `#${anchor}` : ""}`;
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-record underline-offset-4 hover:underline">
      {children ?? <span className="font-mono text-xs">{path}</span>}
      <ExternalLink className="size-3" aria-hidden />
      <span className="sr-only">(opens GitHub in a new tab)</span>
    </a>
  );
}
