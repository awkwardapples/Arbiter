// The review form's rules and words, ported from the Streamlit Review page (ui/screens.py, ui/components.py).

export const OUTCOMES = ["APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"] as const;
export const ROLES = [
  { value: "tprm_analyst", label: "TPRM analyst" },
  { value: "tprm_lead", label: "TPRM lead" },
] as const;
export const MIN_RATIONALE = 30;

/** The fact the policy checks when it applies a precedent (the one mitigation Streamlit offers). */
export const MITIGATIONS = [{ value: "assurance.bridge_letter_current", label: "A current bridge letter covers the gap" }] as const;
export const CONDITIONS = ["SOC 2 Type II report within 60 days", "ISO 27001 certificate within 90 days"] as const;

export interface ReviewBody {
  reviewer: string;
  role: string;
  decision: string;
  rationale: string;
  mitigations: string[];
  conditions: string[];
  create_precedent: boolean;
}

export interface Eligibility {
  eligible: boolean;
  reasons: string[];
}

const REASONS: Record<string, string> = {
  mitigation_not_true: "The mitigation is not confirmed in the evidence, so a precedent could not apply.",
  no_exception_control_failing: "No failing control is one the policy allows an exception for.",
  non_exception_control_failing: "A failing control is one the policy never allows an exception for.",
  reviewer_authority: "The reviewer's role is below the authority the policy requires.",
  reviewer_role_insufficient: "The reviewer's role is below the authority the policy requires.",
  precedent_age: "The precedent is older than the 365-day window.",
  retrieval_quality: "Memory confidence or relevance is below the threshold.",
  tier_risk: "This case's risk tier is higher than the precedent's.",
  no_failing_controls: "No required control is failing, so there is nothing to except.",
  decision_not_approving: "The decision is not an approval, and only an approval can become a precedent.",
};

/** A reason in words; a new code still shows, in sentence case. */
export function reasonWords(code: string): string {
  const known = REASONS[code];
  if (known) return known;
  const words = code.split("_").join(" ");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}.`;
}

export function reviewProblems(body: ReviewBody): Record<string, string> {
  const problems: Record<string, string> = {};
  if (!body.reviewer.trim()) problems.reviewer = "Enter the reviewer's name or email.";
  if (body.rationale.trim().length < MIN_RATIONALE) {
    problems.rationale = `Write at least ${MIN_RATIONALE} characters (${body.rationale.trim().length} so far).`;
  }
  return problems;
}
