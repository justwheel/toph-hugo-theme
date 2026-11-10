#!/usr/bin/env python3
"""Verify a built Hugo site that uses Toph's /llms.txt and source publishing.

The checker works on a finished build directory, never on templates, so it
tests the artifact that actually ships. It has no third-party dependencies:
the runner image is not guaranteed to carry PyYAML, and nothing here needs it.

What it can assert, independently:

  * the index parses as llms.txt (one H1, sections of link entries),
  * every same-origin link in the index resolves to a published file,
  * each entry's rendered-page citation link resolves too,
  * published source files still match their content checkout byte for byte,
  * no published source carries draft front matter,
  * a selected source file was or was not published,
  * a disabled build carries no index, no source tree, and no discovery links,
    including minified HTML where Hugo drops attribute quotes.

Usage:
  check_llms.py --public public --content content \\
      --base-url https://example.org/sub/ --expect enabled

Exit status is 0 when every check passes, 1 otherwise. Failures are printed
one per line with a short reason.

`--expect` sets the default for both halves of the feature; `--expect-index`
and `--expect-sources` override it when a site runs only one of them. Use
`--expect enabled` in CI: leaving it at `auto` would let a total loss of the
feature pass as an intentional disabled build.
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
RENDERED_RE = re.compile(r"\[Rendered page\]\(\s*([^)\s]+)\s*\)")
HEADING_RE = re.compile(r"^(#+) (.+)$")
DRAFT_RE = re.compile(r"^(?:draft:\s*true|:draft:\s*true)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(
    r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))"""
)

FEATURE_TYPES = {"text/markdown", "text/asciidoc"}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def ok(self, message: str) -> None:
        self.notes.append(message)


def link_attributes(tag: str) -> dict[str, str]:
    """Parse a <link> tag's attributes, quoted or minified-unquoted."""
    attributes: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag):
        value = next(group for group in match.groups()[1:] if group is not None)
        attributes[match.group(1).lower()] = value
    return attributes


def feature_links(text: str) -> tuple[bool, bool]:
    """Report (index discovery, per-page source alternate) in rendered HTML."""
    described, source = False, False
    for tag in LINK_RE.findall(text):
        attributes = link_attributes(tag)
        relations = attributes.get("rel", "").lower().split()
        if "describedby" in relations:
            described = True
        if "alternate" in relations and attributes.get("type", "").lower() in FEATURE_TYPES:
            source = True
        if described and source:
            break
    return described, source


def check_inert(public: Path, prefix: str, report: Report, *, index: bool, sources: bool) -> None:
    """A build with the feature disabled must carry no trace of it."""
    if index:
        if (public / "llms.txt").exists():
            report.fail("llms.txt exists but the index is expected to be off")
        else:
            report.ok("no llms.txt index")

    source_root = public / prefix
    if sources:
        files = [path for path in source_root.rglob("*") if path.is_file()] if source_root.is_dir() else []
        if files:
            report.fail(f"{prefix}/ exists with {len(files)} file(s) but sources are expected to be off")
        else:
            report.ok(f"no {prefix}/ source tree")

    offenders: list[tuple[str, Path]] = []
    for html in public.rglob("*.html"):
        try:
            text = html.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # pragma: no cover - unreadable artifact
            report.fail(f"cannot read {html}: {exc}")
            continue
        described, source = feature_links(text)
        if (index and described) or (sources and source):
            offenders.append((html.relative_to(public).as_posix(), html))
    for name, _ in offenders[:3]:
        report.fail(f"{name} carries a feature discovery link while disabled")
    if not offenders:
        report.ok("disabled build carries no feature discovery links")


def check_source_fidelity(
    public: Path,
    content: Path | None,
    prefix: str,
    report: Report,
    expect_source: list[str],
    expect_no_source: list[str],
) -> int:
    """Every published source file must equal its file in the content tree."""
    source_root = public / prefix
    files = sorted(path for path in source_root.rglob("*") if path.is_file()) if source_root.is_dir() else []

    for wanted in expect_source:
        if not (source_root / wanted).is_file():
            report.fail(f"expected source {prefix}/{wanted} was not published")
    for unwanted in expect_no_source:
        if (source_root / unwanted).is_file():
            report.fail(f"source {prefix}/{unwanted} was published but should have been excluded")

    if not files:
        report.fail(f"{prefix}/ is missing or empty from an enabled source export")
        return 0

    compared = 0
    for published in files:
        rel = published.relative_to(source_root)
        parts = rel.parts
        if len(parts) < 2:
            report.fail(f"{published.relative_to(public)} is not language-namespaced")
            continue
        if content is not None:
            original = content / Path(*parts[1:])
            if not original.is_file():
                report.fail(f"{published.relative_to(public)} has no original under {content}")
                continue
            if published.read_bytes() != original.read_bytes():
                report.fail(f"{published.relative_to(public)} differs from {original}")
                continue
            compared += 1
        if DRAFT_RE.search(published.read_text(encoding="utf-8", errors="replace")):
            report.fail(f"{published.relative_to(public)} is a draft and must not be published")

    if content is not None:
        report.ok(f"{compared} published source files match their originals byte for byte")
    else:
        report.ok(f"{len(files)} published source files")
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


def check_index(public: Path, base_url: str | None, prefix: str, report: Report) -> None:
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
    source_links = 0
    current: str | None = None
    section_counts: dict[str, int] = {}
    prefix_path = f"/{prefix.strip('/')}/"
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

        primary = match.group(2)
        if prefix_path in urlparse(primary).path:
            source_links += 1
        targets = [primary]
        rendered = RENDERED_RE.search(match.group(3))
        if rendered:
            targets.append(rendered.group(1))
        for target in targets:
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

    stats = f"llms.txt parsed: 1 H1, {sections} sections, {entries} entries, {len(raw)} bytes"
    if source_links:
        stats += f", {source_links} source links"
    report.ok(stats)
    if source_links == 0:
        report.ok("no index entry links to a source (HTML-only index)")


def resolve_expectation(own: str, overall: str) -> str:
    """Apply the overall expectation to a half that did not state its own."""
    if own != "auto":
        return own
    if overall != "auto":
        return overall
    return "auto"


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
        help="overall expectation; sets the default for both halves",
    )
    parser.add_argument(
        "--expect-index",
        choices=("auto", "enabled", "disabled"),
        default="auto",
        help="override the index expectation (llms.txt)",
    )
    parser.add_argument(
        "--expect-sources",
        choices=("auto", "enabled", "disabled"),
        default="auto",
        help="override the source-export expectation",
    )
    parser.add_argument(
        "--source-prefix",
        default="source",
        help="published source prefix configured in data/llms.yaml (default: source)",
    )
    parser.add_argument(
        "--expect-source",
        action="append",
        default=[],
        metavar="REL",
        help="content-relative source that must be published, language directory first",
    )
    parser.add_argument(
        "--expect-no-source",
        action="append",
        default=[],
        metavar="REL",
        help="content-relative source that must not be published, language directory first",
    )
    args = parser.parse_args()

    public: Path = args.public
    if not public.is_dir():
        print(f"FAIL {public} is not a directory", file=sys.stderr)
        return 1

    prefix = args.source_prefix.strip("/")
    index_expect = resolve_expectation(args.expect_index, args.expect)
    source_expect = resolve_expectation(args.expect_sources, args.expect)

    report = Report()
    index_present = (public / "llms.txt").is_file()

    if index_expect in ("enabled", "auto") and index_present:
        check_index(public, args.base_url, prefix, report)
    elif index_expect == "enabled":
        report.fail("expected an enabled index but llms.txt is missing")

    if index_expect == "disabled" or source_expect == "disabled":
        check_inert(
            public,
            prefix,
            report,
            index=index_expect == "disabled",
            sources=source_expect == "disabled",
        )

    if source_expect in ("enabled", "auto"):
        source_root = public / prefix
        has_sources = source_root.is_dir() and any(path.is_file() for path in source_root.rglob("*"))
        if source_expect == "enabled" and not has_sources:
            report.fail(f"{prefix}/ is missing or empty from an enabled source export")
        if has_sources or args.expect_source or args.expect_no_source:
            check_source_fidelity(
                public,
                args.content,
                prefix,
                report,
                args.expect_source,
                args.expect_no_source,
            )

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
