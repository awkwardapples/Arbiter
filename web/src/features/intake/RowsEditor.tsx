import { Plus, Trash2 } from "lucide-react";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { NativeSelect } from "../../ui/NativeSelect";
import { Textarea } from "../../ui/textarea";
import type { FieldErrors } from "./build";

export interface Column<R> {
  key: keyof R & string;
  label: string;
  kind?: "text" | "date" | "long" | "select";
  options?: readonly string[];
  placeholder?: string;
}

/** An editable table: one row per document or component, with errors under the cell they belong to. */
export function RowsEditor<R extends { [K in keyof R]: string }>({
  name,
  rows,
  columns,
  onChange,
  makeRow,
  addLabel,
  errors,
  emptyText,
}: {
  name: "documents" | "components";
  rows: R[];
  columns: Column<R>[];
  onChange: (rows: R[]) => void;
  makeRow: () => R;
  addLabel: string;
  errors: FieldErrors;
  emptyText: string;
}) {
  const set = (index: number, key: keyof R, value: string) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  return (
    <div className="flex flex-col gap-3" data-testid={`rows-${name}`}>
      {rows.length === 0 ? <p className="text-sm text-graphite">{emptyText}</p> : null}
      {rows.map((row, index) => (
        <div key={index} className="grid gap-3 rounded-panel border border-hairline bg-sheet p-3 md:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
          {columns.map((column) => {
            const error = errors[`${name}.${index}.${column.key}`];
            const label = `${column.label}, row ${index + 1}`;
            const common = {
              "aria-label": label,
              "aria-invalid": error ? true : undefined,
              value: row[column.key],
            };
            const control =
              column.kind === "select" ? (
                <NativeSelect {...common} onChange={(e) => set(index, column.key, e.target.value)}>
                  <option value="">Choose a type</option>
                  {column.options?.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </NativeSelect>
              ) : column.kind === "long" ? (
                <Textarea {...common} placeholder={column.placeholder} onChange={(e) => set(index, column.key, e.target.value)} />
              ) : (
                <Input {...common} placeholder={column.placeholder} onChange={(e) => set(index, column.key, e.target.value)} />
              );
            return (
              <div key={column.key} className={column.kind === "long" ? "md:col-span-4" : undefined}>
                <span className="mb-1 block text-xs font-semibold text-ink" aria-hidden>
                  {column.label}
                </span>
                {control}
                {error ? (
                  <p role="alert" className="mt-1 text-xs text-clash" data-testid={`error-${name}.${index}.${column.key}`}>
                    {error}
                  </p>
                ) : null}
              </div>
            );
          })}
          <div className="flex items-start md:row-start-1 md:col-start-5">
            <Button type="button" variant="ghost" size="icon" aria-label={`Remove row ${index + 1}`} onClick={() => onChange(rows.filter((_, i) => i !== index))}>
              <Trash2 aria-hidden />
            </Button>
          </div>
        </div>
      ))}
      <div>
        <Button type="button" variant="secondary" size="sm" onClick={() => onChange([...rows, makeRow()])}>
          <Plus aria-hidden />
          {addLabel}
        </Button>
      </div>
    </div>
  );
}
