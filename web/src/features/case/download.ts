// Save text as a file in the browser, and copy text with a selection fallback.

export function downloadText(fileName: string, text: string, type = "text/plain;charset=utf-8"): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** Copy with the clipboard API; without it (plain http, old browsers) select the text so Ctrl+C works. */
export async function copyText(text: string, fallback: HTMLTextAreaElement | null): Promise<"copied" | "selected"> {
  try {
    if (!navigator.clipboard) throw new Error("no clipboard");
    await navigator.clipboard.writeText(text);
    return "copied";
  } catch {
    fallback?.focus();
    fallback?.select();
    return "selected";
  }
}
