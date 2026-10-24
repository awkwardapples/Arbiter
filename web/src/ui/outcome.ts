// Outcome colours (design §3.1). The words come from the API when it serves them; otherwise the
// outcome code is put into sentence case, which is the same wording app/labels.py uses for four of five.

export const OUTCOME_CLASS: Record<string, { text: string; border: string; bg: string }> = {
  APPROVE: { text: "text-outcome-approve", border: "border-outcome-approve", bg: "bg-outcome-approve" },
  APPROVE_WITH_CONDITIONS: {
    text: "text-outcome-approve-with-conditions",
    border: "border-outcome-approve-with-conditions",
    bg: "bg-outcome-approve-with-conditions",
  },
  REQUEST_INFO: { text: "text-outcome-request-info", border: "border-outcome-request-info", bg: "bg-outcome-request-info" },
  ESCALATE: { text: "text-outcome-escalate", border: "border-outcome-escalate", bg: "bg-outcome-escalate" },
  DECLINE: { text: "text-outcome-decline", border: "border-outcome-decline", bg: "bg-outcome-decline" },
};

const NEUTRAL = { text: "text-ink", border: "border-ink", bg: "bg-ink" };

export function outcomeClasses(outcome: string | null | undefined) {
  return (outcome && OUTCOME_CLASS[outcome]) || NEUTRAL;
}

export function outcomeWord(outcome: string | null | undefined, label?: string | null): string {
  if (label) return label;
  if (!outcome) return "No outcome";
  const words = outcome.toLowerCase().split("_").join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
