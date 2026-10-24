// Writes dist/.source-hash: sha256 over the sorted POSIX paths and bytes of the console's sources.
// tests/unit/web/test_dist_fresh.py recomputes the same hash in Python; keep the two in step.
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const FILES = [
  "index.html",
  "package-lock.json",
  "vite.config.ts",
  "tailwind.config.js",
  "tailwind.config.ts",
  "postcss.config.js",
  "postcss.config.mjs",
];

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

export function sourceFiles() {
  const paths = walk(join(WEB, "src")).map((p) => relative(WEB, p).split(sep).join("/"));
  for (const name of FILES) if (existsSync(join(WEB, name))) paths.push(name);
  return paths.sort();
}

export function sourceHash() {
  const hash = createHash("sha256");
  for (const rel of sourceFiles()) {
    hash.update(rel, "utf8");
    hash.update("\0");
    hash.update(readFileSync(join(WEB, rel)));
    hash.update("\0");
  }
  return hash.digest("hex");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const digest = sourceHash();
  writeFileSync(join(WEB, "dist", ".source-hash"), `${digest}\n`);
  console.log(`dist/.source-hash ${digest.slice(0, 12)}`);
}
