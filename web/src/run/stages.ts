import { STAGE_NAMES, type Stage, type StageName } from "./types";

/** Orchestrator states (transition events) -> the eleven steps of the stage rail. */
const STATE_TO_STAGE: Record<string, StageName> = {
  INTAKE: "Intake",
  PLAN: "Plan",
  GATHER: "Gather",
  EVALUATE: "Evaluate",
  DECIDE_1: "Decide",
  DECIDE_2: "Decide",
  MEMORY_CHECK: "Memory",
  CHALLENGE: "Challenge",
  REPORT: "Report",
  CONTRACT: "Contract",
  EXECUTE: "Execute",
  DONE: "Done",
};

export function stageFor(state: string): StageName | null {
  return STATE_TO_STAGE[state] ?? null;
}

/** A second decision after memory is the same Decide step, not a new visit. */
export function countsAsVisit(state: string): boolean {
  return state !== "DECIDE_2";
}

export function initialStages(): Stage[] {
  return STAGE_NAMES.map((name) => ({ name, visits: 0, escalated: false }));
}

export const STAGE_WORDS: Record<StageName, string> = {
  Intake: "intake",
  Plan: "planning",
  Gather: "gathering",
  Evaluate: "evaluation",
  Decide: "the decision",
  Memory: "memory",
  Challenge: "the challenge",
  Report: "the report",
  Contract: "the contract",
  Execute: "execution",
  Done: "done",
};
