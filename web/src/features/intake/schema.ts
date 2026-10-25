// Runtime check of the body the New vendor form posts. The type assertions at the foot fail the
// typecheck if this schema drifts from the CaseInput that FastAPI publishes (src/api/schema.d.ts).
import { z } from "zod";
import type { components } from "../../api/schema";
import { CRITICALITIES, DATA_CATEGORIES } from "./options";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

export const answerSchema = z.object({
  question_id: z.string().min(1),
  question: z.string(),
  answer_text: z.string().min(1),
});

export const documentSchema = z.object({
  doc_id: z.string().min(1),
  doc_type: z.string().min(1),
  title: z.string().min(1),
  issued_on: z.string().regex(DATE).nullable().optional(),
  expires_on: z.string().regex(DATE).nullable().optional(),
  text: z.string().min(1),
});

export const componentSchema = z.object({
  product: z.string().min(1),
  vendor: z.string().nullable().optional(),
  version: z.string().nullable().optional(),
});

export const submissionSchema = z.object({
  legal_name: z.string().trim().min(1),
  trading_name: z.string().nullable().optional(),
  category: z.string().min(1),
  requested_service: z.string().trim().min(1),
  criticality: z.enum(CRITICALITIES),
  annual_spend_gbp: z.number().nonnegative(),
  data_categories: z.array(z.enum(DATA_CATEGORIES)).min(1),
  processing_countries: z.array(z.string().min(1)).min(1),
  answers: z.array(answerSchema),
  documents: z.array(documentSchema),
  declared_components: z.array(componentSchema),
  patch_sla_critical_days: z.number().int().nonnegative().nullable().optional(),
});

/** What the questionnaire posts: a submission, never a vendor id. */
export const caseInputSchema = z.object({ submission: submissionSchema });

/** Advanced JSON may also name an existing vendor, as `CaseInput` allows. */
export const pastedCaseInputSchema = z.union([z.object({ vendor_id: z.string().min(1) }), caseInputSchema]);

export type CaseInputBody = z.infer<typeof caseInputSchema>;

type Assert<T extends true> = T;
type Generated = components["schemas"];
export type _BodyIsCaseInput = Assert<CaseInputBody extends Generated["CaseInput"] ? true : false>;
export type _SubmissionMatches = Assert<z.infer<typeof submissionSchema> extends Generated["VendorSubmission"] ? true : false>;
export type _GeneratedFieldsCovered = Assert<
  Exclude<keyof Generated["VendorSubmission"], keyof z.infer<typeof submissionSchema>> extends never ? true : false
>;
