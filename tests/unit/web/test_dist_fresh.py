"""P18B-T9: the committed web console build exists, is complete and matches its sources."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.p18b

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"
DIST = WEB / "dist"
# Same list and order as web/scripts/source-hash.mjs.
HASHED_FILES = (
    "index.html",
    "package-lock.json",
    "vite.config.ts",
    "tailwind.config.js",
    "tailwind.config.ts",
    "postcss.config.js",
    "postcss.config.mjs",
)
ASSET_RE = re.compile(r"""(?:src|href)="(/console/[^"]+)\"""")


def source_hash(web: Path = WEB) -> str:
    """The Python twin of source-hash.mjs: sha256 over sorted POSIX paths and file bytes."""
    paths = [p.relative_to(web).as_posix() for p in (web / "src").rglob("*") if p.is_file()]
    paths += [name for name in HASHED_FILES if (web / name).is_file()]
    digest = hashlib.sha256()
    for rel in sorted(paths):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update((web / rel).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_p18b_t9_dist_index_exists() -> None:
    """P18B-T9: web/dist/index.html is committed."""
    assert (DIST / "index.html").is_file(), "web/dist/index.html is missing: run `npm run build` in web/"


def test_p18b_t9_dist_assets_exist() -> None:
    """P18B-T9: every asset index.html references under /console/ is in web/dist."""
    html = (DIST / "index.html").read_text(encoding="utf-8")
    refs = ASSET_RE.findall(html)
    assert refs, "index.html references no /console/ assets"
    for ref in refs:
        target = DIST / ref.removeprefix("/console/")
        assert target.is_file(), f"{ref} is referenced by web/dist/index.html but missing"


def test_p18b_t9_source_hash_matches() -> None:
    """P18B-T9: web/dist/.source-hash equals the hash of the current sources."""
    recorded = (DIST / ".source-hash").read_text(encoding="utf-8").strip()
    assert recorded == source_hash(), (
        "web/dist is stale against web/src: run `python scripts/tasks.py web-build` and commit web/dist"
    )


def test_p18b_t9_hash_algorithm_is_sensitive(tmp_path: Path) -> None:
    """P18B-T9: the hash changes when a source file changes (so staleness is caught)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    (tmp_path / "index.html").write_text("<html></html>\n", encoding="utf-8")
    before = source_hash(tmp_path)
    (tmp_path / "src" / "a.ts").write_text("export const a = 2;\n", encoding="utf-8")
    assert source_hash(tmp_path) != before
