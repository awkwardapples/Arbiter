// The one orchestrated moment (design §7.4): the stamp, the brief's headline, the facts, two buttons.
// The headline is shown only when this instance's case record came from this very run; never invented.
import { motion } from "motion/react";
import { Link } from "react-router";
import { useCase } from "../api/queries";
import { duration } from "./parse";
import type { RunState } from "./types";
import { Button } from "../ui/button";
import { BorderBeam } from "../ui/effects/BorderBeam";
import { useReducedMotion } from "../ui/effects/useReducedMotion";
import { OutcomeStamp } from "../ui/OutcomeStamp";
import { Serif } from "../ui/Serif";

export function RulingCard({ state, caseId, onWatchAgain }: { state: RunState; caseId: string | null; onWatchAgain: () => void }) {
  const reduced = useReducedMotion();
  const outcome = state.outcome;
  const id = caseId ?? state.caseId;
  const detail = useCase(id, Boolean(outcome));
  if (!outcome) return null;
  const record = detail.data;
  const sameRun = Boolean(record && state.runId && record.trace_path.includes(state.runId));
  const headline = sameRun ? (record?.report.brief?.headline ?? record?.report.summary ?? null) : null;
  const mirror = state.mode?.data === "duckdb";
  const facts = [
    outcome.seconds !== null ? `Took ${duration(outcome.seconds)}` : null,
    `${state.counters.model_calls} model ${state.counters.model_calls === 1 ? "call" : "calls"}`,
    mirror ? `${state.counters.mirror} mirror queries` : `${state.counters.zetaris} Zetaris queries`,
    `${state.fallbacks} ${state.fallbacks === 1 ? "fallback" : "fallbacks"}`,
  ].filter(Boolean);
  return (
    <motion.section
      aria-label="The ruling"
      data-testid="ruling-card"
      initial={reduced ? false : { opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: "easeOut" }}
      className="relative w-[min(440px,100%)] rounded-panel border border-hairline bg-sheet p-3.5 shadow-float"
    >
      <BorderBeam />
      <div className="flex flex-wrap items-center gap-3">
        <OutcomeStamp outcome={outcome.outcome} />
        <span className="text-[13px] text-graphite">{state.policy?.tier ? `Tier ${state.policy.tier}` : null}</span>
      </div>
      {headline ? (
        <Serif className="mt-2 text-sm leading-[22px] font-bold">{headline}</Serif>
      ) : detail.isLoading ? (
        <p className="mt-3 text-sm text-graphite">Fetching the brief…</p>
      ) : (
        <p className="mt-3 text-sm text-graphite">This recording's case record is on the machine that ran it.</p>
      )}
      <p className="mt-2 text-[13px] text-graphite">{facts.join(". ")}.</p>
      <div className="mt-3 flex gap-2">
        {sameRun && id ? (
          <Button asChild>
            <Link to={`/cases/${encodeURIComponent(id)}`}>Open the case</Link>
          </Button>
        ) : null}
        <Button variant="secondary" onClick={onWatchAgain}>
          Watch again
        </Button>
      </div>
    </motion.section>
  );
}
