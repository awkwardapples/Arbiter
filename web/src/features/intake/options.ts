// Choices for the New vendor form, the same lists as the Streamlit form (ui/intake.py).

export const CATEGORIES = ["SaaS", "Internal tools", "Infrastructure", "Professional services", "Hardware", "Other"] as const;
export const CRITICALITIES = ["low", "medium", "high"] as const;
export const DATA_CATEGORIES = ["none", "internal", "personal", "payment", "special_category"] as const;
export const COUNTRIES = ["GB", "IE", "DE", "FR", "NL", "ES", "IT", "US", "CA", "IN", "SG", "AU", "JP"] as const;
export const DOC_TYPES = ["SOC 2 Type II", "ISO 27001", "Penetration test", "Bridge letter", "Other"] as const;
export const CHOICES = ["Yes", "No", "Not answered"] as const;

export type Criticality = (typeof CRITICALITIES)[number];
export type DataCategory = (typeof DATA_CATEGORIES)[number];
export type Choice = (typeof CHOICES)[number];

/** Words for the codes, in sentence case (design §4). */
export const DATA_CATEGORY_WORDS: Record<DataCategory, string> = {
  none: "None",
  internal: "Internal",
  personal: "Personal data",
  payment: "Payment data",
  special_category: "Special category data",
};
export const CRITICALITY_WORDS: Record<Criticality, string> = { low: "Low", medium: "Medium", high: "High" };
