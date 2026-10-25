// Raw JSON behind a disclosure, for the audit file.
export function JsonViewer({ label, value, ...props }: { label: string; value: unknown; "data-testid"?: string }) {
  return (
    <details className="rounded-panel border border-hairline bg-sheet" {...props}>
      <summary className="cursor-pointer px-4 py-2 text-sm font-medium text-ink">{label}</summary>
      <pre className="max-h-[480px] overflow-auto border-t border-hairline bg-well px-4 py-3 font-mono text-xs text-ink">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}
