import { Input } from "../../ui/input";
import { cn } from "../../ui/lib/cn";
import type { AnswerEntry, Question } from "./build";
import { CHOICES, type Choice } from "./options";

/** One questionnaire item: Yes / No / Not answered plus "How?", or one text box. */
export function QuestionField({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: AnswerEntry;
  onChange: (next: AnswerEntry) => void;
}) {
  const qid = question.question_id;
  const choices = (question.options?.length ? question.options : CHOICES) as Choice[];
  return (
    <div className="rounded-panel border border-hairline bg-sheet px-4 py-3" data-testid={`question-${qid}`}>
      <p className="text-sm font-semibold text-ink" id={`q-${qid}`}>
        {question.question}
      </p>
      {question.help ? <p className="text-xs text-graphite">{question.help}</p> : null}
      {question.type === "yes_no" ? (
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <div role="radiogroup" aria-labelledby={`q-${qid}`} className="inline-flex overflow-hidden rounded-[6px] border border-hairline">
            {choices.map((choice) => {
              const on = value.choice === choice;
              return (
                <button
                  key={choice}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => onChange({ ...value, choice })}
                  className={cn(
                    "h-8 border-r border-hairline px-3 text-xs font-medium last:border-r-0",
                    on ? "bg-ink text-sheet" : "bg-sheet text-ink hover:bg-well",
                  )}
                >
                  {choice}
                </button>
              );
            })}
          </div>
          <Input
            aria-label={`How? ${question.question}`}
            placeholder="How? For example AES-256"
            value={value.how}
            onChange={(e) => onChange({ ...value, how: e.target.value })}
            className="min-w-64 flex-1"
            data-testid={`how-${qid}`}
          />
        </div>
      ) : (
        <Input
          aria-labelledby={`q-${qid}`}
          className="mt-2"
          value={value.how}
          onChange={(e) => onChange({ ...value, how: e.target.value })}
          data-testid={`how-${qid}`}
        />
      )}
    </div>
  );
}
