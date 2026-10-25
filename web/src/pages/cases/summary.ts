// The one-sentence portfolio summary (design §12): no big-number tiles.
import { plural } from "../../features/case/words";
import type { QueueItem } from "../../features/case/types";

/** Outcomes that route to the TPRM lead, and the one that waits for the vendor (policy approvals, app/labels.py). */
const LEAD = new Set(["ESCALATE", "DECLINE"]);
const VENDOR = "REQUEST_INFO";

export function summarySentence(items: QueueItem[], pending: number | null): string {
  const lead = items.filter((i) => LEAD.has(i.outcome)).length;
  const vendor = items.filter((i) => i.outcome === VENDOR).length;
  const parts: string[] = [];
  if (lead) parts.push(`${lead} ${lead === 1 ? "needs" : "need"} the TPRM lead`);
  if (vendor) parts.push(`${vendor} ${vendor === 1 ? "is" : "are"} waiting for the vendor`);
  if (pending === null) parts.push("checking for approvals waiting for sign-off");
  else if (pending === 0) parts.push("no approvals are waiting for sign-off");
  else parts.push(`${plural(pending, "approval")} ${pending === 1 ? "is" : "are"} waiting for sign-off`);
  const rest = parts.join("; ");
  return `${plural(items.length, "case")}. ${rest.charAt(0).toUpperCase()}${rest.slice(1)}.`;
}
