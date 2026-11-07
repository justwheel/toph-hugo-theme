#!/usr/bin/env python3
"""Print-mode contrast audit for the Toph theme (toph#82).

Renders pages in print media across a color-mode matrix and reports any text
whose computed color falls below WCAG AA against the paper it lands on.

Two contrast passes are measured for every element that owns a text node:

  * backgrounds off -- Chrome's print default. Paper is plain white.
  * backgrounds on  -- "Background graphics" enabled. Paper is the composite
                      of the element's own and its ancestors' backgrounds.

Why a matrix: print styling is shared, but the color tokens that reach it are
not. Light tokens are baked into the compiled stylesheet, dark tokens arrive
from an inline <style> block, and the no-JS path never sets data-bs-theme at
all. A single crawl cannot prove all four paths, so the default matrix runs
light, dark, and no-JS dark; `--skip-no-js` drops the third.

The audit measures computed CSS, which is what the theme controls. Chromium
then rewrites low-contrast text on its way to paper (`print-color-adjust:
economy`), so these numbers describe the stylesheet rather than the exact ink.

Usage:
    python3 .github/scripts/print_contrast.py --base-url http://localhost:3000/
    python3 .github/scripts/print_contrast.py --base-url http://localhost:3001/ \\
        --forced-dark

The script is intentionally not wired into CI yet; dual-mode auditing belongs
to toph#78. Exit status is 1 when any reading fails, including a color value
the parser cannot read.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

AA_NORMAL = 4.5
AA_LARGE = 3.0
WARN_MARGIN = 4.7

PDF_DIR = Path("/tmp/toph-82-pdf")

# Spot-check pages covering Markdown and AsciiDoc inline code, admonitions,
# quotes, and brand-colored taxonomy UI.
DEFAULT_PDF_PATHS = [
    "/blog/hello-world/",
    "/blog/asciidoc-blogging/",
    "/blog/asciidoc-admonitions/",
    "/blog/blockquote-styling/",
    "/categories/",
    "/tags/",
]

# Walks every element owning a direct text node and returns its resolved color
# plus the background stack that will actually sit behind that text.
COLLECT_JS = """
() => {
  const out = [];
  if (!document.body) return out;
  const describe = (el) => {
    if (el.id) return `${el.tagName.toLowerCase()}#${el.id}`;
    const cls = (el.getAttribute('class') || '')
      .split(/\\s+/)
      .filter(Boolean)
      .slice(0, 3)
      .map((c) => '.' + c)
      .join('');
    return `${el.tagName.toLowerCase()}${cls}`;
  };
  const isVisible = (el) => {
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') return false;
    if (parseFloat(style.opacity) === 0) return false;
    const rects = el.getClientRects();
    if (!rects.length) return false;
    return Array.from(rects).some((r) => r.width > 0 && r.height > 0);
  };
  const backgrounds = (el) => {
    const chain = [];
    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
      chain.push(getComputedStyle(node).backgroundColor);
    }
    return chain;
  };
  // Opacity is not inherited, but it composites a subtree as a group, so every
  // ancestor's value multiplies into the strength of the text under it.
  const inheritedOpacity = (el) => {
    let value = 1;
    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
      value *= parseFloat(getComputedStyle(node).opacity);
    }
    return value;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.nodeType !== Node.TEXT_NODE) continue;
    if (!node.textContent.trim()) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'NOSCRIPT') continue;
    if (!isVisible(el)) continue;
    seen.add(el);
    const style = getComputedStyle(el);
    out.push({
      selector: describe(el),
      page: window.location.pathname,
      color: style.color,
      opacity: inheritedOpacity(el),
      fontSize: parseFloat(style.fontSize),
      fontWeight: parseInt(style.fontWeight, 10) || 400,
      backgrounds: backgrounds(el),
    });
  }
  return out;
}
"""


# Entrance animations (the taxonomy cards fade in with a staggered delay) make
# the first sample non-deterministic: an element caught mid-fade is genuinely
# translucent, so it measures as a much lighter color than it ever prints.
# Jump every animation to its end state before collecting. `finish()` throws on
# infinite animations, so cancel those instead.
SETTLE_JS = """
() => {
  for (const animation of document.getAnimations()) {
    try {
      animation.finish();
    } catch (error) {
      animation.cancel();
    }
  }
  return document.getAnimations().length;
}
"""


@dataclass
class Reading:
    mode: str
    backgrounds_on: bool
    selector: str
    page: str
    color: str
    paper: str
    ratio: float
    threshold: float
    verdict: str  # "pass", "warn", "fail"
    unparsed: bool = False  # color string could not be read at all


@dataclass
class ModeResult:
    mode: str
    readings: list[Reading] = field(default_factory=list)
    pages: int = 0


def parse_color(value: str) -> tuple[float, float, float, float] | None:
    """Parse a Chrome computed color into normalised (r, g, b, a) floats.

    `color-mix()` results are serialized as `color(srgb r g b)` with channels
    in the 0-1 range rather than as `rgb(...)`. The brand `-text` roles are
    color-mix() values, so a parser that skips that form silently skips the
    tokens the audit exists to guard.
    """
    value = value.strip()
    if not value:
        return None
    if value == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    if value.startswith("color("):
        fields = value[value.find("(") + 1 : value.rfind(")")].replace("/", " ").split()
        if not fields or fields[0].lower() != "srgb":
            return None
        try:
            numbers = [
                float(field[:-1]) / 100.0 if field.endswith("%") else float(field)
                for field in fields[1:]
            ]
        except ValueError:
            return None
        if len(numbers) == 3:
            numbers.append(1.0)
        if len(numbers) != 4:
            return None
        red, green, blue, alpha = numbers
        return (red * 255.0, green * 255.0, blue * 255.0, alpha)
    if value.startswith("rgb"):
        numbers = value[value.find("(") + 1 : value.rfind(")")].replace("/", " ").split()
        parts = [p for p in numbers if p not in (",", "")]
        try:
            parts = [float(p.rstrip(",")) for p in parts]
        except ValueError:
            return None
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2], 1.0)
        if len(parts) == 4:
            alpha = parts[3]
            if alpha > 1:
                alpha /= 255.0
            return (parts[0], parts[1], parts[2], alpha)
    return None


def composite_over(top: tuple[float, float, float, float], bottom: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Composite `top` over `bottom` using straight-alpha "over" compositing."""
    ta = top[3]
    ba = bottom[3]
    out_a = ta + ba * (1 - ta)
    if out_a == 0:
        return (0.0, 0.0, 0.0, 0.0)
    out = tuple((top[i] * ta + bottom[i] * ba * (1 - ta)) / out_a for i in range(3))
    return (out[0], out[1], out[2], out_a)


def flatten(chain: list[str], base: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Fold an element's background chain (self first) onto `base` paper."""
    stack = [parse_color(c) for c in chain]
    stack = [c for c in stack if c is not None]
    result = base
    for color in reversed(stack):
        if color[3] == 0:
            continue
        result = composite_over(color, result)
    return result


def relative_luminance(color: tuple[float, float, float, float]) -> float:
    channels = []
    for channel in color[:3]:
        srgb = channel / 255.0
        channels.append(srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    la = relative_luminance(a)
    lb = relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def to_hex(color: tuple[float, float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(round(c)) for c in color[:3]))


def is_large(font_size: float, font_weight: int) -> bool:
    if font_size >= 24:
        return True
    return font_size >= 18.66 and font_weight >= 700


def sitemap_paths(base_url: str) -> list[str]:
    import urllib.request

    root = base_url.rstrip("/") + "/"
    seen_sitemaps: set[str] = set()
    paths: list[str] = []

    def locals_of(element, name: str):
        return [child for child in element if child.tag.split("}")[-1] == name]

    def fetch(url: str) -> None:
        if url in seen_sitemaps:
            return
        seen_sitemaps.add(url)
        with urllib.request.urlopen(url, timeout=30) as response:
            tree = ET.fromstring(response.read())

        kind = tree.tag.split("}")[-1]
        if kind == "sitemapindex":
            for sitemap in locals_of(tree, "sitemap"):
                for loc in locals_of(sitemap, "loc"):
                    if loc.text:
                        fetch(loc.text.strip())
            return

        for url_element in locals_of(tree, "url"):
            for loc in locals_of(url_element, "loc"):
                if not loc.text:
                    continue
                parsed = urlparse(loc.text.strip())
                path = parsed.path or "/"
                if parsed.query:
                    path = f"{path}?{parsed.query}"
                paths.append(path)

    fetch(root + "sitemap.xml")
    # Preserve sitemap order, drop duplicates.
    return list(dict.fromkeys(paths))


def audit_mode(browser, base_url: str, mode: str, color_scheme: str, java_script: bool, paths: list[str]) -> ModeResult:
    result = ModeResult(mode=mode)
    context = browser.new_context(java_script_enabled=java_script, viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.emulate_media(media="print", color_scheme=color_scheme)

    for path in paths:
        try:
            page.goto(base_url.rstrip("/") + path, wait_until="load", timeout=30000)
        except Exception as exc:  # noqa: BLE001 - report and continue the crawl
            print(f"  ! {mode}: {path} failed to load: {exc}", file=sys.stderr)
            continue
        result.pages += 1
        page.evaluate(SETTLE_JS)
        items = page.evaluate(COLLECT_JS)
        for item in items:
            threshold = AA_LARGE if is_large(item["fontSize"], item["fontWeight"]) else AA_NORMAL
            color = parse_color(item["color"])
            if color is None:
                # Never skip a value silently: an unreadable color is exactly
                # the case where a regression could slip through. Report it as
                # a failure so the run exits non-zero and the value is visible.
                result.readings.append(
                    Reading(
                        mode=mode,
                        backgrounds_on=False,
                        selector=item["selector"],
                        page=item["page"],
                        color=item["color"],
                        paper="#ffffff",
                        ratio=0.0,
                        threshold=threshold,
                        verdict="fail",
                        unparsed=True,
                    )
                )
                continue
            # Ancestor opacity dims the text without changing its computed
            # color, so fold it into alpha. This models the text only, not the
            # whole translucent group; print output has no dimmed surfaces.
            alpha = color[3] * item.get("opacity", 1.0)
            effective = (color[0], color[1], color[2], alpha)
            for backgrounds_on in (False, True):
                if backgrounds_on:
                    paper = flatten(item["backgrounds"], (255.0, 255.0, 255.0, 1.0))
                else:
                    paper = (255.0, 255.0, 255.0, 1.0)
                text = composite_over(effective, paper) if alpha < 1 else effective
                ratio = contrast_ratio(text, paper)
                if ratio < threshold:
                    verdict = "fail"
                elif ratio < WARN_MARGIN:
                    verdict = "warn"
                else:
                    verdict = "pass"
                result.readings.append(
                    Reading(
                        mode=mode,
                        backgrounds_on=backgrounds_on,
                        selector=item["selector"],
                        page=item["page"],
                        color=to_hex(text),
                        paper=to_hex(paper),
                        ratio=ratio,
                        threshold=threshold,
                        verdict=verdict,
                    )
                )

    context.close()
    return result


def write_pdfs(browser, base_url: str, mode: str, color_scheme: str, paths: list[str]) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.emulate_media(media="print", color_scheme=color_scheme)
    for path in paths:
        try:
            page.goto(base_url.rstrip("/") + path, wait_until="load", timeout=30000)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! pdf {mode}: {path} failed to load: {exc}", file=sys.stderr)
            continue
        page.evaluate(SETTLE_JS)
        slug = path.strip("/").replace("/", "-") or "root"
        for backgrounds_on in (False, True):
            suffix = "bg-on" if backgrounds_on else "bg-off"
            target = PDF_DIR / f"{mode}-{suffix}-{slug}.pdf"
            page.pdf(path=str(target), print_background=backgrounds_on, format="A4")
    context.close()


def summarise(results: list[ModeResult]) -> tuple[int, int, int]:
    """Print the report. Returns (fails, warns, passes) for unique readings."""
    fails = warns = passes = 0
    for result in results:
        print()
        print("=" * 78)
        print(f"MODE: {result.mode}  ({result.pages} pages)")
        print("=" * 78)
        for backgrounds_on in (False, True):
            label = "backgrounds ON" if backgrounds_on else "backgrounds OFF"
            readings = [r for r in result.readings if r.backgrounds_on is backgrounds_on]
            unique: dict[tuple[str, str, str, str], Reading] = {}
            for reading in readings:
                key = (reading.selector, reading.color, reading.paper, f"{reading.ratio:.2f}")
                if key not in unique or reading.verdict == "fail":
                    unique[key] = reading
            b_fail = sorted((r for r in unique.values() if r.verdict == "fail"), key=lambda r: r.ratio)
            b_warn = sorted((r for r in unique.values() if r.verdict == "warn"), key=lambda r: r.ratio)
            b_pass = [r for r in unique.values() if r.verdict == "pass"]
            fails += len(b_fail)
            warns += len(b_warn)
            passes += len(b_pass)
            print()
            print(f"-- {label}: {len(b_fail)} fail, {len(b_warn)} warn, {len(b_pass)} pass --")
            for reading in b_fail + b_warn:
                if reading.unparsed:
                    print(
                        f"   FAIL unparsed color {reading.color!r}  "
                        f"{reading.selector}  [{reading.page}]"
                    )
                    continue
                print(
                    f"   {reading.verdict.upper():4s} {reading.ratio:5.2f}:1 "
                    f"(need {reading.threshold:.2f}) {reading.color} on {reading.paper}  "
                    f"{reading.selector}  [{reading.page}]"
                )
    print()
    print("-" * 78)
    print(f"TOTAL unique: {fails} fail, {warns} warn, {passes} pass")
    return fails, warns, passes


def main() -> int:
    parser = argparse.ArgumentParser(description="Print-mode contrast audit for Toph.")
    parser.add_argument("--base-url", required=True, help="Base URL of the built site, e.g. http://localhost:3000/")
    parser.add_argument("--path", action="append", dest="paths", help="Path to audit (repeatable). Defaults to sitemap.xml.")
    parser.add_argument(
        "--forced-dark",
        action="store_true",
        help="Audit a build pinned to params.color_mode: dark instead of the auto build.",
    )
    parser.add_argument(
        "--skip-no-js",
        action="store_true",
        help="Drop the no-JavaScript dark cell. It runs by default: Bootstrap falls "
        "back to its light rules there while still reading the theme's variables.",
    )
    parser.add_argument("--pdf", action="store_true", help="Write PDFs for the spot-check pages under /tmp/toph-82-pdf/.")
    parser.add_argument("--pdf-path", action="append", dest="pdf_paths", help="Path to render as PDF (repeatable).")
    args = parser.parse_args()

    paths = args.paths or sitemap_paths(args.base_url)
    pdf_paths = args.pdf_paths or DEFAULT_PDF_PATHS

    matrix = []
    if args.forced_dark:
        matrix.append(("forced-dark", "dark", True))
    else:
        matrix.append(("light", "light", True))
        matrix.append(("dark", "dark", True))
        if not args.skip_no_js:
            matrix.append(("no-js-dark", "dark", False))

    results: list[ModeResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for mode, scheme, java_script in matrix:
            print(f"auditing {mode} ({len(paths)} pages)...", file=sys.stderr)
            results.append(audit_mode(browser, args.base_url, mode, scheme, java_script, paths))
            if args.pdf:
                write_pdfs(browser, args.base_url, mode, scheme, pdf_paths)
        browser.close()

    fails, _, _ = summarise(results)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
