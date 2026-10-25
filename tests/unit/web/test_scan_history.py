"""The history secret scan attributes a deleted file's lines to that file (P18-B, scanner fix)."""

from __future__ import annotations

import pytest

from scripts.scan_secrets import scan_patch

pytestmark = pytest.mark.p18b

FAKE = "sk-" + "a" * 24  # built at runtime so this file holds no literal key shape

PATCH = f"""diff --git a/web/dist/.source-hash b/web/dist/.source-hash
--- a/web/dist/.source-hash
+++ b/web/dist/.source-hash
-0123
+4567
diff --git a/web/dist/assets/index-old.css b/web/dist/assets/index-old.css
deleted file mode 100644
--- a/web/dist/assets/index-old.css
+++ /dev/null
-.x{{--tw-{FAKE}}}
"""


def test_deleted_file_lines_keep_their_own_path() -> None:
    findings = scan_patch(PATCH)
    assert findings, "the fake key was not found at all"
    assert all(f.startswith("web/dist/assets/index-old.css:") for f in findings), findings


def test_deleted_file_respects_its_allowlist_entry() -> None:
    assert scan_patch(PATCH, ["web/dist/assets/*"]) == []


def test_added_file_still_flagged_under_its_name() -> None:
    patch = f"--- /dev/null\n+++ b/app/x.py\n+key = '{FAKE}'\n"
    assert scan_patch(patch)[0].startswith("app/x.py:")
