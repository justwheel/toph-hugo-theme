#!/usr/bin/env bash
# Exercise Toph's /llms.txt feature in both directions against exampleSite.
#
# The committed state of exampleSite/data/llms.yaml is `enabled: true`, because
# the example site is the live demonstration. The first build therefore proves
# the feature works and hands the artifact to check_llms.py, which verifies the
# index structure, link resolution, and byte-for-byte source fidelity. The
# second build flips the flag off in place to prove the feature is genuinely
# inert — no index, no source tree, no discovery links — so a downstream site
# that never opts in is unaffected.
#
# Runs from the theme root. Leaves no changes behind: the data file is restored
# on exit, including on failure.

set -euo pipefail

theme_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$theme_root"

workdir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/toph-llms-XXXXXX")"
data_file="exampleSite/data/llms.yaml"
backup="$workdir/llms.yaml.orig"
cp "$data_file" "$backup"
restore() { cp "$backup" "$data_file"; }
trap restore EXIT

checker=".github/scripts/check_llms.py"

echo "== enabled build (committed state) =="
hugo --source exampleSite --destination "$workdir/on" --logLevel warn
python3 "$checker" \
  --public "$workdir/on" \
  --content exampleSite/content \
  --base-url "https://justwheel.github.io/toph-hugo-theme/" \
  --expect enabled

echo "== disabled build =="
sed -i 's/^enabled: true$/enabled: false/' "$data_file"
if grep -q '^enabled: true$' "$data_file"; then
  echo "FAIL could not disable $data_file" >&2
  exit 1
fi
hugo --source exampleSite --destination "$workdir/off" --logLevel warn
python3 "$checker" --public "$workdir/off" --expect disabled

echo "== ok: feature is verified when enabled and inert when disabled =="
