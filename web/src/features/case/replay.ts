// The result of Replay decision in words (design §4): identical, exactly what differs, or the human override.
import { outcomeWord } from "../../ui/outcome";
import type { ReplayResult } from "./types";
import { checkWord, dayWords, diffWord, listWords, roleWord } from "./words";

export function replaySentence(result: ReplayResult): string {
  const failed = Object.entries(result.checks ?? {})
    .filter(([, ok]) => !ok)
    .map(([key]) => checkWord(key));
  const parts: string[] = [];
  if (result.diff.length) parts.push(`differs in ${listWords(result.diff.map(diffWord))}`);
  if (failed.length) parts.push(`${listWords(failed)} did not verify`);
  const override = result.human_override;
  if (override) {
    const head = result.match ? "Machine decision replays identically" : `Machine decision does not replay identically: it ${parts.join("; ")}`;
    const on = dayWords(override.at);
    return `${head}; the ${roleWord(override.role)} overrode it to ${outcomeWord(override.decision)}${on ? ` on ${on}` : ""}: ${override.rationale}`;
  }
  if (result.match) return "Decision replays identically";
  return parts.length ? `The replay ${parts.join("; ")}.` : "The replay does not match the stored decision.";
}
