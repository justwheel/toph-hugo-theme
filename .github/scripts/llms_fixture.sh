#!/usr/bin/env bash
# Exercise Toph's /llms.txt feature in both directions.
#
# Two jobs, deliberately kept separate:
#
#   1. Verify the artifact the workflow already built. CI builds exampleSite
#      with the Pages baseURL earlier in the job, and that finished directory is
#      handed to check_llms.py. Rebuilding it here would only prove that a
#      second build works, which is not the question.
#
#   2. Prove the opt-out and the configuration guards with a small generated
#      site. The committed exampleSite/data/llms.yaml is never edited: each case
#      writes its own data file into a throwaway site, builds into a fresh
#      destination, and asserts the outcome. A packaging check confirms the theme
#      itself ships no data file, but that is not a substitute for building the
#      disabled cases, which is what catches publication escaping the guard.
#
# Runs from the theme root. Accepts the existing enabled build from
# LLMS_PUBLIC (default exampleSite/public) and its base URL from LLMS_BASE_URL.

set -euo pipefail

theme_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$theme_root"

checker=".github/scripts/check_llms.py"
public="${LLMS_PUBLIC:-exampleSite/public}"
base_url="${LLMS_BASE_URL:-https://justwheel.github.io/toph-hugo-theme/}"
workdir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/toph-llms-XXXXXX")"
mkdir -p "$workdir/themes"
ln -s "$theme_root" "$workdir/themes/toph"
failures=0
example_checksum="$(sha256sum exampleSite/data/llms.yaml | cut -d' ' -f1)"

pass() { printf 'ok   %s\n' "$1"; }
fail() {
  printf 'FAIL %s\n' "$1" >&2
  failures=$((failures + 1))
}

# --- 1. Packaging: the theme must ship no data file ------------------------
if [ -e data/llms.yaml ]; then
  fail "the theme root contains data/llms.yaml, which would enable the feature for every site"
else
  pass "theme ships no data/llms.yaml"
fi

# --- 2. The enabled artifact built earlier in the job ---------------------
if [ -d "$public" ]; then
  if ! python3 "$checker" \
    --public "$public" \
    --content exampleSite/content \
    --base-url "$base_url" \
    --expect enabled \
    --expect-sources enabled; then
    fail "enabled exampleSite build failed verification"
  fi
else
  fail "expected build directory $public does not exist"
fi

# --- 3. Generated fixture site --------------------------------------------
content_src="$workdir/content"
mkdir -p "$content_src/blog"

cat >"$content_src/_index.md" <<'EOF'
---
layout: biography
---
Fixture home page.
EOF

cat >"$content_src/about.md" <<'EOF'
---
title: About
linkTitle: About Link
description: An about page.
---
About body.
EOF

makedoc() {
  local path="$1" title="$2" date="$3"
  cat >"$path" <<EOF
---
title: $title
date: $date
description: $title description.
---
$title body.
EOF
}

makedoc "$content_src/blog/alpha.md" "Alpha" "2024-01-01T00:00:00Z"
makedoc "$content_src/blog/beta.md" "Beta" "2024-01-01T00:00:00Z"
makedoc "$content_src/blog/newest.md" "Newest" "2024-02-01T00:00:00Z"
makedoc "$content_src/blog/future.md" "Future" "2099-01-01T00:00:00Z"
printf -- '---\ntitle: Expired\ndate: 2020-01-01T00:00:00Z\nexpiryDate: 2021-01-01T00:00:00Z\n---\nExpired body.\n' \
  >"$content_src/blog/expired.md"
printf -- '---\ntitle: Draft\ndate: 2024-03-01T00:00:00Z\ndraft: true\n---\nDraft body.\n' \
  >"$content_src/blog/draft.md"
printf -- '---\ntitle: No Render\ndate: 2024-04-01T00:00:00Z\nbuild:\n  render: never\n---\nNo render body.\n' \
  >"$content_src/blog/norender.md"
printf -- '---\ntitle: Alfa\ndate: 2024-01-01T00:00:00Z\ndescription: Spanish alpha.\n---\nAlfa body.\n' \
  >"$content_src/blog/alpha.es.md"

# new_site NAME [DEFAULT_LANG] [LANGUAGES_YAML]
new_site() {
  local name="$1" default_lang="${2:-en}" langs_yaml="${3:-}"
  local dir="$workdir/$name"
  if [ -z "$langs_yaml" ]; then
    langs_yaml='  en:
    weight: 1
  es:
    weight: 2'
  fi
  mkdir -p "$dir/data"
  cp -R "$content_src" "$dir/content"
  cat >"$dir/hugo.yaml" <<EOF
baseURL: https://example.org/sub/
title: Fixture Site
theme: toph
themesDir: $workdir/themes
defaultContentLanguage: $default_lang
languages:
$langs_yaml
disableKinds:
  - taxonomy
  - term
  - RSS
  - sitemap
  - 404
EOF
  printf '%s\n' "$dir"
}

build_site() {
  local dir="$1" out="$2"
  shift 2
  hugo --source "$dir" --destination "$out" --logLevel warn "$@"
}

check() {
  local dir="$1" out="$2"
  shift 2
  python3 "$checker" --public "$out" --content "$dir/content" --base-url "https://example.org/sub/" "$@"
}

section_body() {
  local index="$1" heading="$2"
  awk -v h="## $heading" 'index($0,h)==1{f=1;next} /^## /{f=0} f' "$index"
}

expect_build_failure() {
  local name="$1" dir="$2" needle="$3"
  local log="$workdir/$name.log"
  if build_site "$dir" "$workdir/$name-out" >"$log" 2>&1; then
    fail "$name: build succeeded but should have failed ($needle)"
  elif ! grep -q "$needle" "$log"; then
    fail "$name: build failed without the expected diagnostic ($needle)"
  else
    pass "$name: rejected with a clear diagnostic"
  fi
}

# --- Disabled directions --------------------------------------------------
for name in absent false string-true; do
  dir="$(new_site "$name")"
  case "$name" in
    false)
      cat >"$dir/data/llms.yaml" <<'EOF'
enabled: false
# Ignored entirely while disabled: a disabled site must not need a valid
# index language or resolvable sections.
index:
  language: zz
sections:
  - title: Broken
    pages: [/does-not-exist]
EOF
      ;;
    string-true)
      cat >"$dir/data/llms.yaml" <<'EOF'
enabled: "true"
EOF
      ;;
  esac
  if build_site "$dir" "$workdir/$name-out"; then
    if check "$dir" "$workdir/$name-out" --expect disabled; then
      pass "disabled ($name): inert build"
    else
      fail "disabled ($name): build carries feature output"
    fi
  else
    fail "disabled ($name): build failed"
  fi
done

# --- Enabled fixture cases ------------------------------------------------
dir="$(new_site core)"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
index:
  language: en
sources:
  enabled: true
  prefix: src
  languages: [en]
sections:
  - title: Pages
    pages: [/, /about]
  - title: Featured writing
    section: blog
    featured: [/blog/beta]
    limit: 3
  - title: Chronological
    section: blog
    limit: 10
optional:
  - title: About page
    url: /about
  - title: External
    url: https://example.net/elsewhere
EOF
if build_site "$dir" "$workdir/core-out" && check "$dir" "$workdir/core-out" \
  --expect enabled --expect-sources enabled --source-prefix src \
  --expect-source en/blog/beta.md --expect-no-source es/blog/alpha.es.md; then
  index="$workdir/core-out/llms.txt"
  grep -q '^- \[Fixture Site\]' "$index" && pass "untitled home gets the site title" || fail "untitled home has an empty label"
  grep -q '^- \[About\]' "$index" && pass "entry label prefers .Title over .linkTitle" || fail "entry label used .LinkTitle"
  grep -q -- '- \[About page\](https://example.org/sub/about)$' "$index" && pass "optional URL resolves under a subpath" || fail "optional URL is not subpath-safe"
  grep -q -- '- \[External\](https://example.net/elsewhere)$' "$index" && pass "optional external URL is left alone" || fail "optional external URL was rewritten"
  featured_line="$(grep -n '^## Featured writing$' "$index" | cut -d: -f1)"
  first_featured="$(sed -n "$((featured_line + 1))p" "$index")"
  case "$first_featured" in
    "- [Beta]("*) pass "featured entry leads its section" ;;
    *) fail "featured entry did not lead its section: $first_featured" ;;
  esac
  dup_beta="$(section_body "$index" "Featured writing" | grep -c '^- \[Beta\](' || true)"
  [ "$dup_beta" -eq 1 ] && pass "featured page is not duplicated within its section" || fail "featured page appears twice within its section"
  chrono_line="$(grep -n '^## Chronological$' "$index" | cut -d: -f1)"
  chrono="$(sed -n "$((chrono_line + 1)),$((chrono_line + 3))p" "$index" | sed 's/^- \[\([^]]*\)\].*/\1/' | paste -sd, -)"
  [ "$chrono" = "Newest,Alpha,Beta" ] && pass "date-descending order keeps path-ascending ties" || fail "unexpected chronological order: $chrono"
  for hidden in Future Draft Expired "No Render"; do
    if grep -q "^- \[$hidden\]" "$index"; then fail "$hidden page leaked into the index"; fi
  done
  pass "draft, future, expired, and render-never pages are excluded"
else
  fail "core enabled fixture failed verification"
fi

# --- Empty language list means no sources --------------------------------
dir="$(new_site empty-langs)"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sources:
  languages: []
sections:
  - title: Pages
    pages: [/]
EOF
if build_site "$dir" "$workdir/empty-langs-out" && check "$dir" "$workdir/empty-langs-out" \
  --expect-index enabled --expect-sources disabled; then
  pass "empty sources.languages publishes no source files"
else
  fail "empty sources.languages case failed"
fi

# --- Exact language matching: es must not select es-mx -------------------
dir="$(new_site es-exact en '  en:
    weight: 1
  es:
    weight: 2
  es-mx:
    weight: 3')"
printf -- '---\ntitle: Alfa MX\ndate: 2024-01-01T00:00:00Z\ndescription: Mexican alpha.\n---\nAlfa MX body.\n' \
  >"$dir/content/blog/alpha.es-mx.md"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sources:
  languages: [es]
sections:
  - title: Pages
    pages: [/]
EOF
if build_site "$dir" "$workdir/es-exact-out" && check "$dir" "$workdir/es-exact-out" \
  --expect enabled --expect-sources enabled \
  --expect-source es/blog/alpha.es.md --expect-no-source es-mx/blog/alpha.es-mx.md; then
  pass "exact language membership does not leak across es and es-mx"
else
  fail "exact language selection failed"
fi

# --- Multilingual default is deterministic, not render order -------------
dir="$(new_site default-lang es '  en:
    weight: 1
  es:
    weight: 2
    title: Sitio de prueba')"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sections:
  - title: Pages
    pages: [/]
EOF
if build_site "$dir" "$workdir/default-lang-out"; then
  if check "$dir" "$workdir/default-lang-out" --expect enabled --expect-sources enabled; then
    grep -q '^# Sitio de prueba$' "$workdir/default-lang-out/llms.txt" \
      && pass "index defaults to the configured default content language" \
      || fail "index language did not follow defaultContentLanguage"
    cp "$workdir/default-lang-out/llms.txt" "$workdir/default-lang-first.txt"
    build_site "$dir" "$workdir/default-lang-out2"
    cmp -s "$workdir/default-lang-first.txt" "$workdir/default-lang-out2/llms.txt" \
      && pass "repeated multilingual builds produce identical llms.txt" \
      || fail "llms.txt changed between identical builds"
  else
    fail "multilingual default fixture failed verification"
  fi
else
  fail "multilingual default fixture failed to build"
fi

# --- A site with no English at all ----------------------------------------
dir="$(new_site solo-es es '  es:
    weight: 1
    title: Sitio solo')"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sections:
  - title: Pages
    pages: [/]
EOF
if build_site "$dir" "$workdir/solo-es-out" \
  && check "$dir" "$workdir/solo-es-out" --expect enabled --expect-sources enabled; then
  grep -q '^# Sitio solo$' "$workdir/solo-es-out/llms.txt" \
    && pass "a site with no English indexes its own default language" \
    || fail "single non-English site did not default to its own language"
else
  fail "single non-English fixture failed"
fi

# --- Source-only and index-only switches ---------------------------------
dir="$(new_site source-only)"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
index:
  enabled: false
sources:
  languages: [en]
EOF
if build_site "$dir" "$workdir/source-only-out" && check "$dir" "$workdir/source-only-out" \
  --expect-index disabled --expect-sources enabled --expect-source en/about.md; then
  pass "index can be disabled while sources publish"
else
  fail "source-only configuration failed"
fi

dir="$(new_site index-only)"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sources:
  enabled: false
sections:
  - title: Pages
    pages: [/]
EOF
if build_site "$dir" "$workdir/index-only-out" && check "$dir" "$workdir/index-only-out" \
  --expect-index enabled --expect-sources disabled; then
  pass "sources can be disabled while the index publishes"
else
  fail "index-only configuration failed"
fi

# --- Exclusions and a custom prefix --------------------------------------
dir="$(new_site exclusions)"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sources:
  prefix: originals
  exclude_sections: [blog]
  exclude_pages: [about]
sections:
  - title: Pages
    pages: [/]
EOF
if build_site "$dir" "$workdir/exclusions-out" && check "$dir" "$workdir/exclusions-out" \
  --expect enabled --expect-sources enabled --source-prefix originals \
  --expect-no-source en/about.md --expect-no-source en/blog/alpha.md; then
  pass "exclusions and a custom prefix are honoured"
else
  fail "exclusions or custom prefix failed"
fi

# --- Preview flags must not publish withheld content ---------------------
dir="$(new_site preview)"
cat >"$dir/data/llms.yaml" <<'EOF'
enabled: true
sources:
  languages: [en]
sections:
  - title: Pages
    pages: [/]
  - title: Writing
    section: blog
    limit: 20
EOF
if build_site "$dir" "$workdir/preview-out" --buildDrafts --buildFuture \
  && check "$dir" "$workdir/preview-out" --expect enabled --expect-sources enabled \
    --expect-no-source en/blog/draft.md --expect-no-source en/blog/future.md \
    --expect-no-source en/blog/expired.md; then
  grep -q '^- \[Draft\]' "$workdir/preview-out/llms.txt" && fail "draft leaked into a preview index"
  grep -q '^- \[Future\]' "$workdir/preview-out/llms.txt" && fail "future page leaked into a preview index"
  pass "preview flags do not publish withheld pages"
else
  fail "preview-flag case failed"
fi

# --- Configuration guards fail the build with a diagnostic ---------------
dir="$(new_site bad-language)"
printf 'enabled: true\nsources:\n  languages: [zz]\n' >"$dir/data/llms.yaml"
expect_build_failure bad-language "$dir" 'sources.languages'

dir="$(new_site bad-language-string)"
printf 'enabled: true\nsources:\n  languages: "en ar"\n' >"$dir/data/llms.yaml"
expect_build_failure bad-language-string "$dir" 'sources.languages'

dir="$(new_site bad-index-language)"
printf 'enabled: true\nindex:\n  language: zz\n' >"$dir/data/llms.yaml"
expect_build_failure bad-index-language "$dir" 'index.language'

dir="$(new_site bad-prefix)"
printf 'enabled: true\nsources:\n  prefix: /absolute\n' >"$dir/data/llms.yaml"
expect_build_failure bad-prefix "$dir" 'sources.prefix'

dir="$(new_site stale-taxonomy)"
printf 'enabled: true\nsections:\n  - title: Topics\n    taxonomy: categories\n' >"$dir/data/llms.yaml"
expect_build_failure stale-taxonomy "$dir" 'retired `taxonomy` selector'

dir="$(new_site retired-optional)"
printf 'enabled: true\noptional:\n  - title: Archive\n    page: /blog\n' >"$dir/data/llms.yaml"
expect_build_failure retired-optional "$dir" 'retired `page` field'

dir="$(new_site missing-featured)"
printf 'enabled: true\nsections:\n  - title: Writing\n    section: blog\n    featured: [/blog/nope]\n' >"$dir/data/llms.yaml"
expect_build_failure missing-featured "$dir" 'which does not exist'

dir="$(new_site out-of-section-featured)"
printf 'enabled: true\nsections:\n  - title: Writing\n    section: blog\n    featured: [/about]\n' >"$dir/data/llms.yaml"
expect_build_failure out-of-section-featured "$dir" 'not a published page in section'

# --- The committed example inputs are untouched --------------------------
if [ "$(sha256sum exampleSite/data/llms.yaml | cut -d' ' -f1)" = "$example_checksum" ]; then
  pass "exampleSite/data/llms.yaml was not modified"
else
  fail "the fixture modified exampleSite/data/llms.yaml"
fi

rm -rf "$workdir"

if [ "$failures" -ne 0 ]; then
  printf '%d llms fixture check(s) failed\n' "$failures" >&2
  exit 1
fi

echo "== ok: enabled output verified, disabled output inert, configuration guards hold =="
