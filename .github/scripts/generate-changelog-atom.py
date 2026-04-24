#!/usr/bin/env python3
"""Generate an Atom feed from CHANGELOG.md.

Reads `## [version]` sections in Keep-a-Changelog format from CHANGELOG.md
and emits `changelog.atom` (Atom 1.0) suitable for RSS readers.

Idempotent: if the output matches an existing changelog.atom byte-for-byte,
the file's mtime is still updated but git won't detect a diff, so the
calling workflow won't create a no-op commit.
"""

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

FEED_URL = "https://policycommitment.dictiva.com/changelog.atom"
SITE_URL = "https://policycommitment.dictiva.com/"


def main() -> int:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    # Split by version headings: "## [x.y.z] — ..." or "## [Unreleased]"
    pattern = re.compile(r"^## \[(?P<ver>[^\]]+)\][^\n]*\n", re.MULTILINE)
    matches = list(pattern.finditer(changelog))

    entries = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(changelog)
        body = changelog[start:end].strip()
        if not body:
            continue
        # Skip footnote-link-only sections at end
        lines = [ln for ln in body.splitlines() if ln.strip()]
        if lines and all(ln.startswith("[") and "]:" in ln for ln in lines):
            continue
        entries.append({"version": m.group("ver"), "body": body})

    # Use the CHANGELOG.md's last-commit timestamp so the feed updates
    # exactly when the changelog does.
    try:
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "CHANGELOG.md"]
        ).decode().strip() or datetime.now(timezone.utc).isoformat()
    except Exception:
        ts = datetime.now(timezone.utc).isoformat()

    atom_entries = []
    for e in entries:
        entry_id = f"{SITE_URL}#v{e['version']}"
        title = escape(f"Policy Commitment Attestation — {e['version']}")
        content = escape(e["body"])
        atom_entries.append(
            "  <entry>\n"
            f"    <id>{entry_id}</id>\n"
            f"    <title>{title}</title>\n"
            f"    <updated>{ts}</updated>\n"
            f'    <link rel="alternate" type="text/html" href="{SITE_URL}CHANGELOG.html"/>\n'
            "    <author><name>Policy Commitment Attestation maintainers</name></author>\n"
            f"    <summary>Changes in {escape(e['version'])}.</summary>\n"
            f'    <content type="text">{content}</content>\n'
            "  </entry>"
        )

    atom = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <id>{FEED_URL}</id>\n"
        "  <title>Policy Commitment Attestation — Changelog</title>\n"
        "  <subtitle>Spec changes and release notes for the PCA standard.</subtitle>\n"
        f'  <link rel="self" href="{FEED_URL}"/>\n'
        f'  <link rel="alternate" href="{SITE_URL}CHANGELOG.html"/>\n'
        f"  <updated>{ts}</updated>\n"
        "  <generator>pca-changelog-atom</generator>\n"
        + "\n".join(atom_entries)
        + "\n</feed>\n"
    )

    Path("changelog.atom").write_text(atom, encoding="utf-8")
    print(f"Wrote changelog.atom with {len(entries)} entries.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
