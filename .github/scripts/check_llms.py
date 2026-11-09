#!/usr/bin/env python3
"""Verify a built Hugo site that uses Toph's /llms.txt and source publishing.

The checker works on a finished build directory, never on templates, so it
tests the artifact that actually ships. It has no third-party dependencies:
the runner image is not guaranteed to carry PyYAML, and nothing here needs it.

When the feature is off it asserts that the build is genuinely inert.
When it is on it checks four independent things:

  * the index parses as llms.txt (one H1, sections of link entries),
  * every same-origin link in the index resolves to a published file,
  * every published source file still matches its content-checkout original
    byte for byte,
  * no source file carries draft front matter.

Usage:
  check_llms.py --public public --content content \\
      --base-url https://example.org/sub/

Exit status is 0 when every check passes, 1 otherwise. Failures are printed
one per line with a short reason.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# `- [label](target): note` and the variant with no note. The label may hold
# backslash-escaped brackets, so a naive `[^\]]*` would stop too early.
ENTRY_RE = re.compile(r"^- \[((?:\\.|[^\\\]])*)\]\(\s*([^)\s]+)\s*\)(.*)$")
HEADING_RE = re.compile(r"^(#+) (.+)$")
DRAFT_RE = re.compile(r"^draft:\s*true\s*$", re.MULTILINE)


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def ok(self, message: str) -> None:
        self.notes.append(message)


def check_inert(public: Path, report: Report) -> None:
    """A build with the feature disabled must carry no trace of it."""
    if (public / "llms.txt").exists():
        report.fail("llms.txt exists but the feature is expected to be off")
    source = public / "source"
    if source.exists():
        report.fail("source/ exists but the feature is expected to be off")

    offenders = []
    for html in public.rglob("*.html"):
        try:
            text = html.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # pragma: no cover - unreadable artifact
            report.fail(f"cannot read {html}: {exc}")
            continue
        if 'rel="describedby"' in text:
            offenders.append(html)
            if len(offenders) >= 3:
                break
    for html in offenders:
        report.fail(f"{html.relative_to(public)} carries llms.txt discovery while disabled")
    if not offenders:
        report.ok("disabled build carries no llms.txt, no source/, no discovery links")


def check_source_fidelity(public: Path, content: Path, report: Report) -> int:
    """Every published source file must equal its file in the content tree."""
    source = public / "source"
    if not source.is_dir():
        report.fail("source/ is missing from an enabled build")
        return 0

    files = sorted(p for p in source.rglob("*") if p.is_file())
    if not files:
        report.fail("source/ is empty")
        return 0

    for published in files:
        rel = published.relative_to(source)
        parts = rel.parts
        if len(parts) < 2:
            report.fail(f"{published.relative_to(public)} is not language-namespaced")
            continue
        original = content / Path(*parts[1:])
        if not original.is_file():
            report.fail(f"{published.relative_to(public)} has no original under {content}")
            continue
        if published.read_bytes() != original.read_bytes():
            report.fail(f"{published.relative_to(public)} differs from {original}")
            continue
        if DRAFT_RE.search(published.read_text(encoding="utf-8", errors="replace")):
            report.fail(f"{published.relative_to(public)} is a draft and must not be published")
    report.ok(f"{len(files)} published source files match their originals byte for byte")
    return len(files)


def local_path(public: Path, url: str, base_url: str | None) -> Path | None:
    """Map a link target onto the build directory, or None if it is foreign."""
    parsed = urlparse(url)
    path = parsed.path

    if base_url:
        base = urlparse(base_url)
        if parsed.netloc and base.netloc and parsed.netloc != base.netloc:
            return None
        base_path = base.path or "/"
        if path != base_path.rstrip("/") and not path.startswith(base_path):
            return None
        path = path[len(base_path) :] if path.startswith(base_path) else ""
    elif parsed.netloc:
        # No base URL supplied: only site-root-relative links can be checked.
        return None

    path = unquote(path)
    if not path or path.endswith("/"):
        path += "index.html"
    return public / path.lstrip("/")


def check_index(public: Path, base_url: str | None, report: Report) -> None:
    index = public / "llms.txt"
    if not index.is_file():
        report.fail("llms.txt is missing from an enabled build")
        return

    raw = index.read_bytes()
    text = raw.decode("utf-8")
    if not raw.endswith(b"\n"):
        report.fail("llms.txt does not end with a newline")
    if "\r\n" in text:
        report.fail("llms.txt uses CRLF line endings")

    lines = text.splitlines()
    h1 = [line for line in lines if HEADING_RE.match(line) and HEADING_RE.match(line).group(1) == "#"]
    if len(h1) != 1:
        report.fail(f"llms.txt must have exactly one H1, found {len(h1)}")
    elif lines and not HEADING_RE.match(lines[0]).group(1) == "#":
        report.fail("llms.txt must start with its H1")

    sections = 0
    entries = 0
    current: str | None = None
    section_counts: dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading and heading.group(1) == "##":
            current = heading.group(2)
            if current in section_counts:
                report.fail(f"llms.txt repeats the section {current!r}")
            section_counts[current] = 0
            sections += 1
            continue
        if not line.startswith("- "):
            continue
        match = ENTRY_RE.match(line)
        if not match:
            report.fail(f"llms.txt:{number} is not a parseable link entry")
            continue
        entries += 1
        if current is None:
            report.fail(f"llms.txt:{number} appears before any section heading")
        else:
            section_counts[current] += 1
        target = match.group(2)
        resolved = local_path(public, target, base_url)
        if resolved is None:
            continue
        if resolved.is_dir():
            resolved = resolved / "index.html"
        if not resolved.is_file():
            report.fail(f"llms.txt:{number} links to {target}, which is not in the build")

    if sections == 0:
        report.fail("llms.txt has no sections")
    for name, count in section_counts.items():
        if count == 0:
            report.fail(f"llms.txt section {name!r} is empty")
    report.ok(f"llms.txt parsed: 1 H1, {sections} sections, {entries} entries")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", required=True, type=Path, help="Hugo publish directory")
    parser.add_argument("--content", type=Path, help="content checkout, for fidelity checks")
    parser.add_argument(
        "--base-url",
        help="site baseURL, so absolute links in llms.txt can be resolved",
    )
    parser.add_argument(
        "--expect",
        choices=("auto", "enabled", "disabled"),
        default="auto",
        help="force an expectation instead of inferring it from llms.txt",
    )
    args = parser.parse_args()

    public: Path = args.public
    if not public.is_dir():
        print(f"FAIL {public} is not a directory", file=sys.stderr)
        return 1

    report = Report()
    enabled = (public / "llms.txt").is_file()
    if args.expect == "enabled" and not enabled:
        report.fail("expected an enabled build but llms.txt is missing")
    elif args.expect == "disabled":
        enabled = False

    if enabled:
        check_index(public, args.base_url, report)
        if args.content:
            check_source_fidelity(public, args.content, report)
    else:
        check_inert(public, report)

    for failure in report.failures:
        print(f"FAIL {failure}")
    for note in report.notes:
        print(f"ok   {note}")

    if report.failures:
        print(f"\n{len(report.failures)} check(s) failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
