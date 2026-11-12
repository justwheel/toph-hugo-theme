#!/usr/bin/env bash
# Exercise Toph's /llms.txt feature in both directions.
#
#   1. Verify the build the workflow already produced; a fresh build here would
#      only prove that a second build works.
#   2. Build one tiny site through the promises that matter: the opt-out guard
#      (absent data, `false`, string `"true"`), exact language selection, and a
#      `render: link` page staying out of the index and the source export.
#
# Runs from the theme root. Takes the build from LLMS_PUBLIC (default
# exampleSite/public) and its base URL from LLMS_BASE_URL.

set -euo pipefail

theme_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$theme_root"
checker=".github/scripts/check_llms.py"
public="${LLMS_PUBLIC:-exampleSite/public}"
base_url="${LLMS_BASE_URL:-https://justwheel.github.io/toph-hugo-theme/}"
workdir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/toph-llms-XXXXXX")"
trap 'rm -rf "$workdir"' EXIT
site="$workdir/site"
mkdir -p "$site/content/blog" "$site/data" "$workdir/themes"
ln -s "$theme_root" "$workdir/themes/toph"
failures=0
pass() { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1" >&2; failures=$((failures + 1)); }

# 1. Packaging: a data file at the theme root would enable every site.
if [ -e data/llms.yaml ]; then
  fail "the theme root contains data/llms.yaml"
else
  pass "theme ships no data/llms.yaml"
fi

# 2. The enabled artifact built earlier in the job.
if python3 "$checker" --public "$public" --content exampleSite/content \
  --base-url "$base_url" --expect enabled --expect-sources enabled; then
  pass "enabled exampleSite build verified"
else
  fail "enabled exampleSite build failed verification"
fi

# 3. Opt-out: absent, `false`, and string `"true"` each build inert.
printf -- '---\nlayout: biography\n---\nHome.\n' >"$site/content/_index.md"
printf -- '---\ntitle: About\n---\nAbout.\n' >"$site/content/about.md"
printf -- '---\ntitle: Alpha\ndate: 2024-01-01T00:00:00Z\n---\nAlpha.\n' >"$site/content/blog/alpha.md"
printf -- '---\ntitle: Alfa\ndate: 2024-01-01T00:00:00Z\n---\nAlfa.\n' >"$site/content/blog/alpha.es.md"
printf -- '---\ntitle: Alfa MX\ndate: 2024-01-01T00:00:00Z\n---\nAlfa MX.\n' >"$site/content/blog/alpha.es-mx.md"
cat >"$site/hugo.yaml" <<EOF
baseURL: https://example.org/sub/
title: Fixture Site
theme: toph
themesDir: $workdir/themes
languages:
  en: {weight: 1}
  es: {weight: 2}
  es-mx: {weight: 3}
disableKinds: [taxonomy, term, RSS, sitemap, 404]
EOF
for case in absent false string-true; do
  rm -f "$site/data/llms.yaml"
  case "$case" in
    false) printf 'enabled: false\n' >"$site/data/llms.yaml" ;;
    string-true) printf 'enabled: "true"\n' >"$site/data/llms.yaml" ;;
  esac
  out="$workdir/out-$case"
  if hugo --source "$site" --destination "$out" --logLevel warn --minify \
    && grep -q '<html' "$out/index.html" \
    && python3 "$checker" --public "$out" --content "$site/content" \
      --base-url "https://example.org/sub/" --expect disabled; then
    pass "disabled ($case): inert build"
  else
    fail "disabled ($case): build failed or carried feature output"
  fi
done

# 4. Exact language selection: es must not publish es-mx. The index is Spanish
#    so the listed link-only page is resolved in the same language it would be
#    filtered through, and the assertions below prove the render check, not the
#    language selector, is what excludes it.
printf -- '---\ntitle: Linked Only\ndate: 2024-01-01T00:00:00Z\nbuild:\n  render: link\napi_key: SENTINEL-NOT-A-SECRET\n---\nLinked only body.\n' >"$site/content/blog/linked-only.es.md"
cat >"$site/data/llms.yaml" <<'EOF'
enabled: true
index:
  language: es
sources:
  languages: [es]
sections:
  - title: Pages
    pages: [/, /blog/alpha, /blog/linked-only]
EOF
out="$workdir/out-es"
if hugo --source "$site" --destination "$out" --logLevel warn \
  && python3 "$checker" --public "$out" --content "$site/content" \
    --base-url "https://example.org/sub/" --expect enabled --expect-sources enabled \
    --expect-source es/blog/alpha.es.md --expect-no-source es-mx/blog/alpha.es-mx.md \
    --expect-no-source es/blog/linked-only.es.md \
  && [ ! -d "$out/es/blog/linked-only" ] \
  && ! grep -q 'linked-only' "$out/llms.txt"; then
  pass "exact language selection, and a render: link page is neither published nor indexed"
else
  fail "exact language selection or render: link withholding failed"
fi
if [ "$failures" -ne 0 ]; then
  printf '%d llms fixture check(s) failed\n' "$failures" >&2
  exit 1
fi
echo "== ok: enabled artifact verified, opt-out inert, language selection exact, link-only page withheld =="
