# AGENTS.md

This file provides guidance to AI agents — OpenCode, Codex, Claude Code, and any other harness — when working with code in this repository.
It covers behavior that holds for any downstream site; site-specific editorial policy, taxonomy decisions, deployment details, and harness environment facts belong in that site's own `AGENTS.md`.


## Project overview

Toph is a lightweight, responsive Hugo theme for biography and portfolio sites, built on Bootstrap 5.3 and licensed MPL-2.0. It features project profiles, dynamic footer badges, a data-driven social media system, blogging with taxonomy support, and Schema.org SEO.

- **Hugo minimum version**: 0.166.0 Extended (required for `resources.Publish` and contextual `.Render`); local development and CI are currently pinned to 0.169.0
- **Bootstrap CSS**: 5.3.8, vendored at `assets/vendor/bootstrap/bootstrap.min.css` — bumping it is a manual chore (see "External resources")
- **Bootstrap JS**: 5.3.8 via CDN, loaded with `defer` at end of body by `partials/footer.html`
- **Bootstrap Icons**: 1.11.3, vendored at `assets/vendor/bootstrap-icons/` with both font formats and the upstream MIT license
- **Google Fonts**: fetched and republished locally at build time by `partials/fonts.html`
- **Content formats**: Markdown and AsciiDoc (via Asciidoctor)
- **Example site**: `exampleSite/` — deployed to GitHub Pages as a live demo

### AsciiDoc parity (non-negotiable)

AsciiDoc is a first-class content format. **Any feature built for Markdown MUST also work for AsciiDoc.** A change that ships for one format only is incomplete.

Asciidoctor bypasses Hugo's render hooks, so AsciiDoc often needs a separate implementation reaching the same result — heading anchors, for example, use a render hook for Markdown and `replaceRE` on `.Content` for AsciiDoc, producing identical markup and sharing one stylesheet.

To detect AsciiDoc, use `.File.Ext == "adoc"`. Do **not** use `.Markup` — it returns an object, not a string, in Hugo 0.157+, so string comparison silently fails.


## Build commands

All Hugo commands run from the `exampleSite/` directory because the theme lives one level up:

```bash
# Development server
cd exampleSite && hugo server --buildDrafts

# Production build
cd exampleSite && hugo --minify

# Build with a specific baseURL (required for local Pa11y testing)
cd exampleSite && hugo --minify --baseURL http://localhost:3000/
```

Asciidoctor must be installed for `.adoc` content (`gem install asciidoctor`).


## CI pipeline

The GitHub Actions workflow (`.github/workflows/hugo.yml`) runs on all pushes and PRs targeting `main`:

1. Installs Hugo Extended, Dart Sass, Node.js 24, pa11y-ci, serve, and Asciidoctor
2. Builds the site with the GitHub Pages baseURL
3. **Verifies the `/llms.txt` feature** with `.github/scripts/llms_fixture.sh`: the enabled checker runs against the build step's artifact, then one small generated site covers the three opt-out values, exact language selection, and a `render: link` page that must stay unindexed and unpublished (see "Machine-readable index and source files")
4. **Rebuilds with `--baseURL http://localhost:3000/`** for Pa11y (critical — without this, Chromium fetches stale CSS from the deployed site instead of freshly built assets)
5. Runs Pa11y accessibility audit against all sitemap URLs
6. Rebuilds again with the Pages baseURL for the deployment artifact
7. Deploys to GitHub Pages (only on `main`)

CI tools live in `.github/package.json` (pa11y-ci, serve). Install with `npm ci --prefix .github`.
`.github/scripts/check_llms.py` uses only the Python standard library, because the runner image is not guaranteed to carry PyYAML.

**Pa11y accessibility rules**: Only errors fail the build (`includeWarnings` is OFF). HTMLCS transparency checks (G18.Abs) are warnings, not errors.


## Architecture

### Layout hierarchy

```
baseof.html          HTML skeleton: head, nav, header, <main>, footer
  _default/
    biography.html   Biography layout: hero, for-hire, content, recent-posts, projects, team
    card.html        Card content view for recent-posts (featured, grid variants)
    li.html          List item content view for paginated listings (list.html, term.html)
    list.html        Paginated content list with excerpts
    single.html      Single page with blog guards ($is_structural, $is_blog_post)
    rss.xml          RSS 2.0 feed with full content, cover images, and <enclosure>
    terms.html       Fallback taxonomy terms list with sort toggle
    term.html        Fallback single term page with pagination
  team/
    list.html        Team section list page with card grid
  tweets/
    single.html      Standalone archived tweet page with full-width card
  blog/
    list.html        Blog archive with year/month Bootstrap accordion
  categories/
    terms.html       Magazine-style category cards with images + recent posts
  tags/
    terms.html       Word cloud with scaled sizing + sort toggle
```

### Homepage architecture & fallback trap

The theme intentionally does not provide a default `layouts/index.html` template.
Downstream sites must explicitly declare their desired homepage layout (such as `layout: biography`) in their `_index.md` or `_index.adoc` front matter, or provide a site-level `layouts/index.html`.
If an index page lacks a layout declaration, Hugo silently falls back to `_default/list.html` without warnings, rendering a paginated list of all regular pages (including `projects/`, `team/`, and `footer/` because `list.html` does not filter `hide_sitemap: true`).

### Key partials

| Partial | Purpose |
|---------|---------|
| `head.html` | Meta, CSS variables from config, stylesheet links (vendored Bootstrap and Icons, `main.css`) |
| `fonts.html` | Fetches the Google Fonts stylesheet at build time, republishes each woff2 locally, and inlines the rewritten `@font-face` rules |
| `font-weight.html` | Normalizes a configured `fonts.*_weight` into a CSS value and a `:wght@…` fragment; see "Heading and body font-weight binding" |
| `nav.html` | Fixed navbar with hover-triggered dropdowns, social links from data registry, translation selector |
| `hero.html` | Compact centered hero: profile photo, tagline, social icons, about link |
| `header.html` | Page title (`biography.name` on home, `.Title` elsewhere) |
| `footer.html` | Footer badges + footer-box (configurable license, repo link); also loads the deferred Bootstrap JS bundle, which every page needs for Bootstrap's declarative `data-bs-*` attributes |
| `meta-seo.html` | Canonical URL, description, and Schema.org Person/Article JSON-LD |
| `meta-social.html` | OpenGraph and Twitter Card metadata with resolved featured-image URLs |
| `pagination.html` | Bootstrap 5 pagination with i18n and ARIA labels |
| `post-meta.html` | Date, updated, author, reading time, word count, taxonomy badges |
| `post-nav.html` | Prev/next post navigation within section |
| `recent-posts.html` | Homepage: 1 featured + 4 secondary cards with stretched links |
| `render-page-content.html` | Renders page content and post-processes AsciiDoc heading anchors and subpath-relative links |
| `resolve-image-path.html` | Shared image path resolution: handles remote URLs (https://), protocol-relative (//), absolute (/path), and relative (filename) paths |
| `llms/*.html` | Opt-in `/llms.txt` and native source publishing; inert without `data/llms.yaml` (see "Machine-readable index and source files") |
| `projects.html` | Project profiles with icons; receives filtered collection from caller |
| `projects-carousel.html` | Image carousel above projects; receives filtered collection from caller |
| `team.html` | Homepage team card grid; receives filtered collection from caller |
| `team-card-photo.html` | Team member photo: local assets (Hugo `.Fill` + WebP) or remote URLs |
| `for-hire.html` | Optional hire-me banner |

### Data-driven social media

Social platforms are defined in `data/social.yaml` as a registry of 11 platforms, each with a `name`, `url` template (using `%s` for the username), and Bootstrap `icon` class. Site config references platforms by registry key (e.g., `social.github: "username"`). The nav partial and hero partial both look up platforms via `hugo.Data.social`.

Config keys in `params.social` **must match** `data/social.yaml` keys exactly. Mismatched keys silently produce no output.

The LinkedIn URL template is generic (`.../%s`) to support both personal (`in/user`) and company (`company/name`) profiles. Mastodon uses `%s` directly (expects a full URL).

### CSS architecture

Styles are processed by Hugo's `css.Build` function, which resolves `@import` statements into a single output file at build time and injects the light-mode custom properties as build vars. The template in `head.html` uses:

```go-html-template
{{- $css := resources.Get "css/main.css" | css.Build (dict "vars" $vars) | fingerprint }}
```

`$vars` merges brand colors and fonts from site config with the flattened `light:` half of `data/style.yaml`. `main.css` exposes them through `@import 'hugo:vars'`.

#### File structure

```
assets/css/
  main.css                        @import entrypoint (no CSS rules)
  base/
    _global.css                   Body, headings, anchor links
    _nav.css                      Fixed navbar, dropdowns, hover states
    _content.css                  Main body: links, images, figures, ToC, profile
    _print.css                    Print stylesheet: hides navbar/UI, page numbering
    _rtl.css                      Right-to-left layout overrides (Arabic)
  components/
    _cover.css                    Cover image for blog posts
    _hero.css                     Homepage hero section
    _post-meta.css                Blog post metadata bar
    _post-nav.css                 Prev/next post navigation
    _asciidoc-admonition.css      AsciiDoc admonition blocks (note, tip, warning…)
    _blockquote.css               Blockquotes and verse blocks (Markdown & AsciiDoc)
    _code.css                     Code block borders
    _pdf-download.css             PDF download shortcode card
    _team.css                     Team member card grid
    _tweet-archive.css            Archived tweet card, image grid, lightbox modal
    _footer.css                   Footer badges and footer-box
  taxonomy/
    _terms-controls.css           Sort toggle controls
    _term-excerpt.css             Term page excerpts
    _categories.css               Categories grid layout
    _tags.css                     Tags word cloud
  blog/
    _recent-posts.css             Homepage recent posts cards
    _blog-archive.css             Blog archive accordion
```

#### Rules for modifying CSS

1. **Never add CSS rules to `main.css`** — it is an import-only entrypoint.
2. **Edit the appropriate partial** for the component you are changing. Each file corresponds to a specific layout partial or page template, noted in its section comment header.
3. **To add a new component**, create a new `_component-name.css` file in the appropriate directory (`base/`, `components/`, `taxonomy/`, or `blog/`) and add an `@import` line to `main.css` in the matching group.
4. **All color values must use CSS custom properties** — never hardcode hex values, `rgba()`, or named colors anywhere under `assets/css/`. There is no `_variables.css`; the neutral palette lives in `data/style.yaml`. Add new neutral values there under **both** the `light:` and `dark:` subtrees, then reference them with `var()`.
5. **Colors reach CSS from two places, neither of them a CSS file.** Light-mode values (brand from site config, neutral from `data/style.yaml`) are baked into the compiled stylesheet by `css.Build` vars, which `main.css` pulls in via `@import 'hugo:vars'`. Dark-mode values are emitted as an inline `<style>` block in `head.html`. See "Dark mode" below.
6. **Underscore prefix convention**: partial filenames start with `_` to signal they are not standalone stylesheets.

#### Key specificity pattern

`main a { color: var(--text-link) }` (specificity 0,0,1,1) overrides bare class selectors on `<a>` elements inside `<main>`. Badge and link classes that need their own color must be prefixed with `main a.classname` (specificity 0,0,2,1) to win.

### Dark mode

Toph ships a switchable light/dark theme driven by the `color_mode` site param: `auto` (default — follow the OS, with a navbar toggle), `light`, or `dark`.

#### The palette: `data/style.yaml`

Every neutral group in `data/style.yaml` has parallel `light:` and `dark:` subtrees with the same keys. `head.html` flattens each into a CSS variable by joining group and key with a hyphen, so `text.light.body` and `text.dark.body` both become `--text-body` — in different scopes.

A group may be dark-only by omitting its `light:` subtree; the light range then finds nothing and emits nothing.
A group may also be light-only, by omitting its `dark:` subtree, which keeps its values constant across modes.
`print:` is that case: paper does not change with the color mode, so `@media print` in `_print.css` remaps every mode-dependent token to it and the dark `<style>` block can never override those values.
The `bs:` group overrides Bootstrap's own tokens: surface variables are dark-only, while `--bs-code-color` is configured across both modes.

**Invariant for `bs:` tokens:** Every key under `light:` must also appear under `dark:`.
The theme's `:root` block from `main.css` loads after `bootstrap.min.css`.
Because `:root` and `[data-bs-theme=dark]` share specificity `(0,1,0)`, an unpaired light token outranks Bootstrap's dark default whenever `data-bs-theme="dark"` is set.
Without JS, Bootstrap falls back to light rules that read the same variable.
An unpaired light token therefore lands on a dark surface in every mode.

#### How the two modes are emitted

Light and dark travel by deliberately different routes, and the distinction matters when debugging:

- **Light** is baked into the compiled, fingerprinted stylesheet through `css.Build` vars. It is the default state of `:root`.
- **Dark** is emitted as an inline `<style>` block in `head.html`, because it must be able to change without rebuilding the stylesheet.

The dark declarations are flattened **once** into a `$decls` string, then emitted in two scopes:

1. `:root[data-bs-theme="dark"]` — set by the toggle's JavaScript.
2. `@media (prefers-color-scheme: dark) { :root:not([data-bs-theme]) { … } }` — the no-JS fallback, emitted only in `auto` mode.

Never let those two lists drift apart. Emitting `$decls` twice is what guarantees they cannot.

#### Brand colors in dark mode

`colors.dark.*` supplies primary, secondary, accent, and background, each falling back to its light counterpart. The `-text` roles are **not** Hugo-interpolated: they are literal `color-mix(in srgb, var(--primary) 60%, white)` strings resolved by the browser, so text tracks whatever the dark brand color actually is. `safeCSS` is required on the emitted declarations — `color-mix()` contains a `%`, which Go's contextual auto-escaping inside `<style>` would otherwise corrupt.

### Structural vs. blog content

`single.html` uses guards to distinguish structural content (projects, footer badges, team members) from blog posts:
- **`$is_structural`**: pages whose categories overlap with `params.taxonomy_exclude` or have `hide_sitemap: true`
- **`$is_blog_post`**: non-structural pages with a publication date

Blog features (post-meta, post-nav, ToC) only render for blog posts.

### Render hooks and shared partials

- `_default/_markup/render-heading.html` — Adds anchor links to Markdown headings (AsciiDoc headings are post-processed with `replaceRE` in `partials/render-page-content.html`)
- `_default/_markup/render-image.html` — Wraps images in `<figure>/<figcaption>` when a title is provided
- `_default/_markup/render-link.html` — Resolves internal **Markdown** links against `.Page.GetPage` and `relURL` so links respect subpath `baseURL` deployments.
  Hugo's `relURL`/`absURL` treat a leading slash as domain-root-relative, so strip it before passing a local root-relative path when the configured baseURL path must be retained.
  AsciiDoc bypasses render hooks, so `partials/render-page-content.html` applies equivalent root-relative link rebasing and heading-anchor post-processing across full page-body output: single and biography pages, section and taxonomy layouts, embedded projects and footer pages, standalone tweets, and RSS descriptions.
- `partials/resolve-image-path.html` — Shared image path resolution used by `single.html` (cover images), `rss.xml` (feed images), and `meta-social.html` (social cards and Schema.org Article images). Accepts `dict "src" $src "file" .File` and returns the resolved path. Handles remote URLs (`https://`), protocol-relative URLs (`//`), absolute paths (`/path`), and relative filenames (resolved via `.File`).
  Pass `"absolute" true` when the consumer requires an absolute URL; local paths are passed to `absURL` without their leading slash so a `baseURL` subpath is retained.
- `partials/meta-social.html` — Emits OpenGraph and Twitter Card metadata using `resolve-image-path.html`, avoiding Hugo's built-in templates' inability to resolve relative images for standalone content files.

#### Page-body rendering is a theme contract

**Use `partial "render-page-content.html" <page>` when emitting a full page body from a layout or page-composition partial, including RSS descriptions.**
This is an intentional departure from Hugo's customary direct `{{ .Content }}` output, not redundant indirection to simplify away.
Hugo still owns content conversion: the helper reads the page's already-rendered `.Content`, passes Markdown through unchanged, and applies the theme's AsciiDoc-specific post-processing.
It does not replace Hugo's markup engine or ask authors to use a different content format.

**Why the helper is necessary:** Goldmark invokes Hugo render hooks, but Asciidoctor does not.
Direct `.Content` output therefore includes the theme's heading anchors and internal-link handling for Markdown while silently omitting those features for AsciiDoc.
In a subpath deployment, an AsciiDoc `href="/blog/"` escapes the configured site prefix and points at the domain root; it can look correct in a root-domain development build while failing on a GitHub Pages project site.
Checking only `single.html` is insufficient because section introductions, taxonomy descriptions, embedded projects, footer pages, standalone tweets, and RSS descriptions are separate content-output paths.
PR #100's review exposed this exact coverage gap after the helper initially reached only single and biography layouts.

**Call-site rules:** Pass the page whose body is being rendered, including an embedded term or project page, rather than the containing page or an HTML string.
The helper needs that page's `.File.Ext` to identify AsciiDoc reliably.
Keep page context when testing for optional content: use `if .Content` followed by the helper, rather than `with .Content` followed by `{{ . }}`, which rebinds the context to the rendered HTML and bypasses processing.
Reading `.Content` inside the helper or checking whether content exists is valid; the contract governs emitting page bodies, not every property access.
Likewise, a fetched resource's `.Content`, such as the Google Fonts stylesheet, is not a page body and does not belong in this helper.
Shortcodes that embed another page's content require separate consideration of both the embedded page and the host's rendering path: the current single-pass rebasing is not idempotent, so do not blindly introduce a second processing pass.

**Do not revert helper calls to direct `.Content` output merely to match Hugo convention or shorten a template.**
A replacement is justified only by a concrete rendering defect, a measured cost, or an upstream capability that makes this compatibility layer unnecessary.
Such a change must preserve heading-anchor and root-relative-link behavior for both Markdown and AsciiDoc across every affected output path, including embedded page contexts and feeds.
Enumerate the callers, verify root and subpath builds, check excluded external/protocol-relative/fragment links, and document the replacement mechanism and evidence before removing the helper.
A successful Hugo build or a correct Markdown single page alone does not establish parity.

### Shortcodes

- `pdf-download.html` — Styled download card for local PDF files with auto-computed file size via `os.Stat`. Parameters: `file` (path in `static/`), `title`, optional `description`. CSS in `assets/css/components/_pdf-download.css`.
- `tweet-archive.html` — Embeds an archived tweet from the local content archive. Looks up a tweet content page by its `tweet_id` front matter param and renders a styled card with author info, tweet text, image grid, and a link to the standalone archived tweet page. Clicking any image opens a full-screen Bootstrap modal carousel that starts on the clicked image. CSS in `assets/css/components/_tweet-archive.css`.

### Tweet archive

Toph includes a self-hosted tweet archive system for preserving tweets from deleted or inaccessible accounts.
Each archived tweet is a Hugo page bundle in the site's `content/tweets/<tweet-id>/` directory with images stored alongside the `index.md` file.

#### Content model

Tweet page bundles use the following front matter:

```yaml
title: "Archived Tweet — @mention1 #hashtag1"
date: 2020-01-31T13:53:32+00:00
tweet_id: "1223242916988096512"
author: "username"
author_name: "Display Name"
categories: ["tweets"]
```

- `tweet_id` (required): The original tweet ID. The `tweet-archive` shortcode uses this to look up the content page.
- `author`: The Twitter/X handle (without @).
- `author_name`: Display name shown in the card header. Falls back to `site.Params.biography.name`.
- `avatar`: Optional profile photo path. Falls back to `site.Params.images[0]` (the site logo).
- `title`: Should include "Archived Tweet" plus @mentions and #hashtags from the tweet text, for SEO indexing. No `<a>` links — plain text only.
- Tweet pages should NOT use `hide_sitemap: true` — they are designed to be indexed by search engines.

Tweet body text goes after the front matter as standard Markdown content.
@mentions should be linked as `[@handle](https://x.com/handle)` and #hashtags as `[#tag](https://x.com/hashtag/tag)`.
Images are stored as `photo1.jpg`, `photo2.jpg`, etc. in the page bundle directory.

#### Layout

- `layouts/tweets/single.html` — Standalone tweet page using the full viewport width. Renders the same card component as the shortcode but without the "View archived tweet" link.
- The shortcode renders a centered 550px-max card within blog post content.

#### Image grid behavior

The image grid adapts to the number of photos:
- 1 photo: Full-width, natural aspect ratio
- 2 photos: Side-by-side, equal width
- 3 photos: First photo full-width on top, two smaller photos side-by-side below
- 4 photos: 2×2 grid

Clicking any image opens a Bootstrap modal carousel lightbox starting on the clicked photo.

#### Shortcode usage

```
{{</* tweet-archive id="1223242916988096512" */>}}
```

The `id` parameter must match a content page's `tweet_id` front matter. If no matching page is found, Hugo will error at build time.

#### Accessibility

- Card uses `<figure>` with `role="figure"` and `aria-label`
- Tweet text uses `<blockquote cite="">` for semantic accuracy
- Footer uses `<figcaption>`
- Each image button has a descriptive `aria-label` ("View photo 1 of 4 in full screen")
- Modal has `aria-label` for screen readers, close button has descriptive label
- Image buttons have `:focus-visible` outline for keyboard navigation
- `prefers-reduced-motion` disables hover transitions

### i18n

Translation files in `i18n/`: `en.yaml`, `es.yaml`, `ar.yaml`, `hi.yaml`. All four are enabled in the example site config with explicit weights (`en: 1`, `ar: 2`, `hi: 3`, `es: 4`), so every language is exercised by a CI build. Namespaces: `404_page`, `footer`, `hero`, `hire_me`, `index`, `misc`, `nav`, `recent_posts`, `tweet_archive`, sorted alphabetically within each file. Coverage is **not** uniform: `ar.yaml` and `hi.yaml` carry seven namespaces, omitting `hire_me` and `index`, so `partials/for-hire.html` falls back to English on those two languages. The `index` namespace is referenced by no layout at all and is a cleanup candidate in either direction — finish it or drop it.

### Archetypes

- `default.md` — Generic content
- `blog.md` — Markdown blog post with title, date, draft, categories, tags, author, description, images, and toc
- `blog.adoc` — AsciiDoc blog post with the same front matter, minus `toc`

Hugo selects an archetype by file extension.
Without `blog.adoc`, `hugo new blog/post.adoc` fell back to Hugo's built-in stub with only `title`, `date`, and `draft`.
Keep both blog archetypes in sync when a front-matter field is added, so Markdown and AsciiDoc posts start from the same scaffold.
AsciiDoc posts enable a table of contents with the `:toc:` document attribute instead of the `toc` front-matter key.

## Machine-readable index and source files

`layouts/partials/llms/` publishes an `/llms.txt` index and an unmodified copy of the source file behind every published page.
The user-facing documentation is in `README.md` under the same heading; this section records what a template author must not break.

- **Opt-in is a hard requirement.** The feature reads `hugo.Data.llms` and does nothing unless `enabled` is the YAML boolean `true`.
  An absent file, `enabled: false`, or `enabled` written as the string `"true"` must all produce zero output — a theme upgrade must never switch this on for anyone.
  The string form warns and stays inert; it must not fail the build, because an inert build is the promise.
  Toph ships no data file at the theme root, and that is what keeps the promise: never add one.
  `exampleSite/data/llms.yaml` is switched on because the example site is the demonstration, not because the theme has a default.
  `llms/config.html` returns early when the feature is disabled, so a disabled site is never asked for a valid index language or resolvable sections.

- **Publication uses `resources.FromString` + `.Publish`, not output formats.** That is deliberate and load-bearing: `outputs` is not merged from a theme config, and a `home` output format would have to survive the `layout: biography` lookup.
  Do not "simplify" this into a custom output format without accepting that every downstream site would then have to edit `outputs` itself.

- **Sources are the complete files.** Read them with `os.ReadFile .File.Filename`; `.RawContent` drops front matter and `.Content` is rendered HTML.
  Byte fidelity is CI-checked, so any normalization, trimming, or rewriting shows up immediately as a failure.

- **Source eligibility lives in `llms/eligible.html`, which defers the shared publication rule to `llms/published.html`.** Drafts and pages outside their publish window are excluded even when a developer passes `--buildDrafts` or `--buildFuture`.
  Source-language selection is an exact list membership against `sources.langs`, with `sources.all` as a separate flag: never compare language codes with a substring test, and never let an explicit empty list fall back to "all" through truthiness.
  `hide_sitemap` and `taxonomy_exclude` are **not** consulted — they describe listing behavior, and reusing them here would drop public project pages.

- **The publication rule lives in `llms/published.html`.** Both index selectors, `featured`, and source eligibility call it, so drafts, pages outside their publish window, and pages with no rendered output are excluded once, before they can consume a section's `limit`.
  Filtering on `.Draft` alone leaves future and expired pages in an index built with preview flags.
  A non-empty `RelPermalink` does not prove output exists: `build.render: link` keeps a permalink and writes no HTML, so the rule reads the effective render mode from `.Params.build`, which reports a `cascade` inherited value too.
  Source eligibility adds its own file-extension, language, and exclusion tests on top; the shared rule never looks for a backing file, because a generated term page is public HTML with no source.

- **`partialCached` is a cache, not a once-only lock.** `llms/publish.html` is keyed on the language and may be evaluated more than once under concurrency, so every write must be deterministic and idempotent.
  Do not add a mutable "already published" flag.

- **Selection order must be deterministic.** Hugo 0.169.0's collection `sort` uses a stable sort, so `llms/select.html` orders with two passes — path ascending, then date descending — and equal dates keep their path-ascending order.
  Do not reintroduce a composite rank key; do not use `.ByDate.Reverse`, which reverses equal-date groups too.
  Two builds of the same checkout must produce identical `llms.txt` bytes.

- **The globally cached config must not read render-order state.** `llms/config.html` is cached under a single key, so its defaults come from `hugo.Sites.Default.Language.Lang` and from the matching entry in `hugo.Sites`, never from `site.Language.Lang` or `site.Title`.
  A language-dependent default inside that file would make the index language depend on which page rendered first.

- **Text handling goes through `llms/text.html`.** `plainify` strips tags but leaves entities, so `htmlUnescape` follows it; `truncate` is avoided because on a string it emits HTML entities.
  The index is built as a slice of lines joined by explicit newlines and never emitted through an HTML output action, which is what keeps Go's contextual auto-escaping out of the file.

- **AsciiDoc parity is by construction.** Both formats are published natively, so there is no conversion branch to keep in sync.
  The `<link rel="alternate">` type comes from `.File.Ext`: `text/asciidoc` for `.adoc`, `text/markdown` otherwise.
  Never label an AsciiDoc source as Markdown.

- **HTTP `Content-Type` is the host's decision.** Hugo knows both media types and the `<link>` elements advertise them, but GitHub Pages offers no per-repository MIME mapping.
  Do not claim format-specific response headers without checking a real deployment.

- **Verification is CI-enforced.** `.github/scripts/check_llms.py` checks index structure, source and citation link resolution, byte fidelity, exact language selection, and inert output against a finished build.
  `.github/scripts/llms_fixture.sh` runs the enabled checker against the build the workflow already produced, then rebuilds one small generated site through the three opt-out values, the exact-language case, and a `render: link` page that must stay unindexed and unpublished.
  It must never edit the committed `exampleSite/data/llms.yaml`.
  Both scripts run in the theme workflow, and every enabled invocation passes `--expect enabled`: `--expect auto` would let a total feature loss pass as an intentional opt-out.

### Hugo API facts this feature depends on

Each of these cost a debugging round; none is obvious from the documentation.

- **`site.Pages` is language-scoped; `site.AllPages` is not.** `site.AllPages` mixes every language of a multilingual build and is deprecated as of 0.156, so an enumeration must start from `site.Pages`.
- **`hugo.Sites.Default.Language.Lang` is the configured default content language**, and it does not depend on which language rendered the template. `hugo.Sites` is ordered by language weight and `hugo.Sites.Default` is a `Site`, so its `.Title` is the default language's title. Inside a globally `partialCached` config, `site.Language.Lang` and `site.Title` are the wrong source: they follow whichever page rendered first.
- **`collections.Sort` is stable.** `tpl/collections/sort.go` uses `sort.Stable` in 0.169.0 (and `resources/page/pages_sort.go` does the same), so a two-pass sort is a deterministic way to express a primary and a tie-breaker. `.ByDate.Reverse` is different: reversing a date sort also reverses equal-date groups.
- **`with` treats an empty slice as false, but `isset` tests key presence.** Use `isset $m "languages"` for any list where an explicit empty value is meaningful; `with` would silently apply the default instead.
- **`.ExpiryDate` is always a `time.Time`**, zero when unset, so `lt .ExpiryDate now` is true for every page that has no expiry. Guard with `.ExpiryDate.IsZero` before comparing; `.PublishDate` needs the same guard for pages with no date.
- **YAML integers arrive as `uint64`** through `hugo.Data`, not `int`. A validation that tests `printf "%T"` against `"int"` rejects every value a user writes.
- **`reflect.IsString` and `reflect.IsBool` do not exist.** Hugo's `reflect` namespace offers only `IsMap` and `IsSlice`; for scalars, compare `printf "%T"` or use `eq` against a literal (which returns false, not an error, on a type mismatch).
- **`resources.FromString` publishes at exactly the target path given**, and its `.RelPermalink` carries the configured `baseURL` subpath, so no manual URL joining is needed. Spaces in the path are percent-encoded by `.RelPermalink`, and `--minify` leaves text resources untouched.
- **`truncate` escapes its input as HTML**, and `plainify` does not decode entities — hence the `plainify` then `htmlUnescape` order in `llms/text.html`.
- **`errorf` logs and fails the build but does not stop template execution**, so a guard that emits an error must also avoid running the code that depends on the missing value. Go template variables are block-scoped, so a value assigned inside `if` is not visible after `end`.


## Hugo template conventions

### Global `site` function (ALWAYS use)

Always use Hugo's global `site` function to access site-level data in templates.
Never use `$.Site` or `.Site`.

| Use this | Not this |
|----------|----------|
| `site.Title` | `$.Site.Title` or `.Site.Title` |
| `site.Params.description` | `$.Site.Params.description` |
| `site.BaseURL` | `$.Site.BaseURL` |

The global `site` function is not context-dependent — it works correctly inside `with`, `range`, and other blocks that rebind the `.` context.
`$.Site` requires the root template context to be available, which breaks if the template is refactored or nested inside a block that shadows `$`.
The global function is shorter, more idiomatic, and eliminates an entire class of scoping bugs.

When modifying existing templates that use `$.Site` or `.Site`, convert them to `site` as part of the change.
Do not leave mixed usage in the same file.

### Reserved front-matter fields use Page methods (Hugo 0.169.0+)

Hugo v0.169.0 deprecated reading reserved front-matter fields through `.Params` or `.Param` — the lookups are redirected to the corresponding `Page` method and logged as deprecated, and the redirect will be removed in a future release.

| Use this | Not this |
|----------|----------|
| `.Title` | `.Params.title` or `.Param "title"` |
| `.Date` | `.Params.date` or `.Param "date"` |
| `.Description` | `.Params.description` or `.Param "description"` |

- Namespaced `.Param` lookups are unaffected and remain correct: `.Param "icon"`, `.Param "author"`, `.Param "hire_me"`, `.Param "biography.name"`, `.Param "colors.*"`, `.Param "fonts.*"`.
- `where` lookups over non-reserved fields are likewise unaffected: `"Params.tweet_id"`, `"Params.hide_sitemap"`.
- Site config stays on `site.Params.*` (e.g., `site.Params.description`) — the deprecation governs **page** front matter, not site configuration.
- The migration is tracked in toph#103.

### JSON-LD structured data

Use `| jsonify | safeJS` when outputting dynamic values inside `<script type="application/ld+json">` blocks.
The `jsonify` filter handles quoting and escaping special characters (double quotes, newlines) correctly.
The `safeJS` filter prevents Hugo from HTML-escaping the JSON output inside `<script>` tags.

For arrays and slices (e.g., `sameAs`, `knowsAbout`), pass the entire slice to `jsonify` rather than manually iterating with comma tracking.

### Image processing: .Fill vs .Resize and Smart crop behavior

Hugo's `.Fill` method is specifically a crop-and-resize operator whose default anchor is `Smart` (entropy and edge detection).
On square or near-square portrait images (such as profile photos, hero avatars, or logos), `Smart` crop shifts the bounding box toward the detected focal point, cutting off edges (such as the bottom ~10% of a portrait).
When combined with CSS circular clipping (`border-radius: 50%`), this compounding effect can noticeably alter the composition by cropping into the subject (chin, collar, or shoulders).
To scale an image proportionally without cropping any pixels, use `.Resize` (e.g., `.Resize "500x webp"` or `.Resize "280x webp"`).
If `.Fill` is required to conform non-square source images to a square aspect ratio, specify an explicit anchor such as `Center` (e.g., `.Fill "500x500 webp Center"`) rather than relying on `Smart` crop defaults.
Always guard image processing operations with `reflect.IsImageResourceProcessable $resource` to ensure the file is a valid, processable raster format before invoking `.Fill` or `.Resize`.

### Hero image processing and CLS avoidance

The hero section (`hero.html`) standardizes consistently on `.Resize "500x webp"` and `.Resize "280x webp"` for all hero images, avoiding `.Fill` so rectangular logos, wordmarks, and portrait photos scale without pixel cropping.
When `params.hero.shape` is `"circle"` (default), CSS `border-radius: 50%` masks the image.
When `params.hero.shape` is `"square"` (or `"none"`), `.hero-photo-square` leaves all corners unmasked.
For processable raster images, `width="{{ $heroDesktop.Width }}" height="{{ $heroDesktop.Height }}"` provides the browser with the exact intrinsic aspect ratio to guarantee zero Cumulative Layout Shift (`CLS = 0`).
For non-processable fallback assets (such as SVGs), the `height="250"` attribute is omitted when shape is square so that `.hero-photo { height: auto }` scales the image naturally without reserving a false 1:1 square box.

### Heading and body font-weight binding

Theme typography binds configured Google Fonts weights (`fonts.title_weight`, `fonts.header_weight`, and `fonts.default_weight`) directly into CSS custom properties (`--title-font-weight`, `--header-font-weight`, `--default-font-weight`).
In `head.html`, the `partials/font-weight.html` helper normalizes clean numeric weights (e.g., `700`, `500`) into both CSS variables and `:wght@...` Google Fonts query strings, while safely handling legacy query syntax without concatenating italic flags or variable ranges.
Unconfigured heading weights default to `"500"` in `head.html` to preserve Bootstrap typography parity rather than inheriting body weight (`400`).
All headings (`h1` and `h2`–`h6`, `#toctitle`, `.navbar-brand`) and `body` are bound in `_global.css` and `_nav.css` to ensure a consistent sitewide typographic hierarchy.

### Deterministic multilingual builds

Site configurations defining multiple languages must provide explicit `weight:` values for each language under `languages:` (e.g., `en: 1`, `ar: 2`, `hi: 3`, `es: 4`).
Without explicit weights, Hugo's `range .AllTranslations` emits `hreflang` tags and navigation dropdown items in an unstable, non-deterministic order across builds.


## WCAG AA accessibility

This project enforces WCAG AA contrast ratios via Pa11y CI:
- **4.5:1** for normal text, **3:1** for large text and non-text UI
- Minimum accessible gray on white background: `#767676` (4.54:1)
- All muted text uses `#767676` in light mode; never use `#888` or lighter grays
- Chroma syntax highlighting theme is `github` (passes WCAG AA; `monokai` does not)
- Navbar dropdowns are hover-triggered (no `data-bs-toggle="dropdown"`) using the `.nav-hover-dropdown` class — all dropdowns must use this pattern
- Bootstrap `.dropdown-item` defaults to dark text — must override `color: var(--secondary)` for colored dropdown backgrounds

### Verify contrast against the lightest surface, not the background

A dark text color that clears AA against the page background can still fail on cards, list-group items, accordions, and hover states, which sit several steps lighter. **Check every text role against the lightest surface it can land on**, then walk back down. Calibrating the dark ramp against the page background alone once failed 355 of 495 audited URLs while the page itself looked fine.

The dark text ramp deliberately targets roughly **6:1** on that lightest surface rather than the 4.5:1 floor. The compliant-but-dim alternative was genuinely hard to read, and the headroom costs nothing.

### Bootstrap dark mode is attribute-gated

Bootstrap 5.3's dark component styles are gated **exclusively** on `[data-bs-theme=dark]`. Bootstrap ships **no** `prefers-color-scheme` rules of its own. Two consequences:

1. On the no-JS fallback that attribute is absent, so `.card`, `.list-group-item`, and `.accordion` fall back to Bootstrap's **light** rules — while still reading whatever `--bs-*` variables the theme has redefined.
2. Therefore, **never override Bootstrap's background tokens without the matching foreground tokens.** Overriding `--bs-body-bg` alone left Bootstrap's light `--bs-body-color` painted on a dark surface at 1.07:1 — invisible text for anyone whose JavaScript was disabled or failed to load.

Override the surface set as a unit (`--bs-body-bg`, `--bs-tertiary-bg`, `--bs-secondary-bg`, `--bs-body-color`, `--bs-secondary-color`, `--bs-tertiary-color`, `--bs-emphasis-color`, `--bs-border-color`) and point them at the theme's own `var(--…)` values so both scopes resolve identically.

Bootstrap's hover surface is `--bs-tertiary-bg` and its active surface is `--bs-secondary-bg`. Map them to match the bespoke components' convention: hover lighter, active darker.

### Testing dark mode

Headless Chrome defaults `prefers-color-scheme` to **light**, so a default Pa11y run exercises **light mode**, not dark. To test dark mode, emulate it explicitly (or use a `--config` overlay pinning `params.color_mode: dark` — forced modes render server-side, so the crawl is deterministic). To reproduce the no-JS path, disable JavaScript *and* emulate dark — the bug class above is invisible with JavaScript on.

### Print is a third rendering target

Printing is not a variant of light mode.
`assets/css/base/_print.css` remaps every token that `head.html` emits for dark mode onto the light-only `print:` group in `data/style.yaml`, using selectors specific enough (`html:root[data-bs-theme]`, `html:root:not([data-bs-theme])`) to outrank both dark `<style>` blocks regardless of source order.
A document printed from a dark page must be identical to one printed from a light page.

When you add a color token, add it to the dark subtree **and** to the print remap, or it leaks the dark value onto paper.
Brand-colored surfaces (badges, tags, the footer box, the PDF download card) carry `--secondary` text tuned for a colored background.
Chrome drops backgrounds when printing, so each of those needs an explicit ink-on-paper override rather than a token remap.

`.github/scripts/print_contrast.py` audits this.
It reads the print-media computed color of every element owning a text node, on every sitemap URL, and checks it against a plain-white paper and against a composited-background paper, failing below WCAG AA.
Its default matrix runs light, dark, and no-JS dark, because the no-JS path never sets `data-bs-theme` and falls back to Bootstrap's light rules; `--skip-no-js` drops that cell.
Run it against an `auto` build and against a `params.color_mode: dark` build; it is deliberately not wired into CI yet (toph#78).
An unreadable color value is reported as a failure rather than skipped, so an unsupported serialization cannot hide a regression.

The audit measures computed CSS, which is what the theme controls.
Chromium's default `print-color-adjust: economy` rewrites low-contrast text on its way to paper — `#767676` is embedded as `#212121` — so these numbers describe the stylesheet, not the exact ink.


## Performance

### Measure before optimizing, and attribute the metric

Never assume which element is the Largest Contentful Paint. Read it from `lcp-breakdown-insight` — `.details.items[1]` names the actual DOM node, and `.details.items[0]` splits the metric into time-to-first-byte, load delay, load time, and element render delay. Two rounds of image optimization were once spent on a downstream site before anyone checked, and the LCP element turned out to be a text paragraph with no image on the critical path at all. A text LCP is gated by render-blocking stylesheets, not by bytes, so the whole optimization strategy differs.

**Lighthouse 13 renamed the diagnostic audits to `*-insight`.** `render-blocking-resources` no longer exists; it is `render-blocking-insight`. The same applies to `cache-insight`, `lcp-breakdown-insight`, `third-parties-insight`, `font-display-insight`, and others. Enumerate what is actually present with `jq -r '.audits | keys[] | select(test("insight"))'` before querying. A `jq` lookup of a stale audit name with a `// []` fallback returns empty and reads as "no problems found" — that exact mistake sent an investigation down a wrong path for several rounds.

**Isolate a suspected culprit by blocking it, rather than reasoning from the waterfall.** `--blocked-url-patterns` is repeatable:

```bash
npx lighthouse@latest <url> --form-factor=mobile --screenEmulation.mobile \
  --blocked-url-patterns='*googletagmanager.com*' --blocked-url-patterns='*bootstrap-icons*'
```

Run four to six times per condition and compare distributions. Single runs are not trustworthy — production runs on one build varied from Performance 66 to 94, and that spread was analytics contention rather than anything about the page. Analytics moves Total Blocking Time, not LCP; do not let the two be conflated.

## Security

### Secrets and credentials

Never commit plaintext credentials, API keys, tokens, passwords, or private keys to this repository. It is public — anything pushed is permanently exposed.

**Before staging any commit**, check for:
- API keys, access tokens, or secrets in config files, templates, or content
- `.env` files, `credentials.json`, service account keys, or SSH private keys
- Hardcoded URLs containing tokens or authentication parameters (e.g., `?key=...`, `?token=...`)
- Hugo config values that look like real credentials rather than example placeholders

The example site config (`exampleSite/config.yaml`) must only contain demonstrative, non-sensitive values. If a feature requires an API key or secret (e.g., analytics, comment systems), document the config key with a placeholder like `"YOUR_API_KEY_HERE"` and note in comments that the real value should come from an environment variable or a file excluded by `.gitignore`.

### Template output safety

Hugo auto-escapes template output by default. Preserve this behavior:
- **Never use `safeHTML`, `safeJS`, or `safeURL`** unless the input is fully controlled by the theme (not user content). Each use is a potential XSS vector — justify it in a code comment if unavoidable.
- Treat all `.Params` values, `.Content`, and front matter fields as untrusted input. Hugo's auto-escaping handles this correctly as long as `safe*` functions are not applied.
- Validate that `href` and `src` attributes built from config or params cannot inject `javascript:` URIs.

### External resources

Render-blocking assets are served from our own origin, because every third-party origin on the critical path costs a DNS lookup and a TLS handshake before the page can paint (toph#79, toph#94).
Bootstrap JS remains on a CDN, deferred at the end of the body.
Google Fonts' build-time failure fallback can still introduce external stylesheets; verify the generated output before claiming that a build has no third-party render-blocking requests.

Bootstrap Icons previously incurred **780 ms of render-blocking delay** against a downstream production site in October 2026, more than the vendored Bootstrap CSS (312 ms) and `main.css` (156 ms) combined.
Vendoring removes that cold cross-origin connection while preserving the `bi-*` class contract used by `data/social.yaml` and downstream sites.
The pristine stylesheet references both `.woff2` and `.woff` files relative to its own directory, including upstream query strings.
Keep both fonts alongside it and explicitly publish them from `head.html`; fingerprinting the CSS alone does not publish those dependencies.
Check font loading under both root and subpath deployments, and measure production performance after deployment rather than treating the historical delay as a guaranteed saving.

**Vendored assets** (`assets/vendor/`) are checked in, reviewed at commit time, and fingerprinted by Hugo, which emits the `integrity` attribute itself. This is a *smaller* trust surface than a CDN — the bytes cannot change without a commit. The honest cost is that nobody bumps the version for us: upstream tracking is manual.

When vendoring or bumping a vendored asset:
- Download from the official distribution, then verify its SHA384 against the publisher's own published SRI hash before committing
- Keep the file pristine — do not reformat or strip trailing comments, or the hash check stops working on the next bump
- Bump any companion file in the same commit. Bootstrap's pristine CSS retains its `sourceMappingURL`, so `bootstrap.min.css.map` must move with it or DevTools 404s against a stale map
- Hugo publishes an asset only when a template touches it, so a companion file that no template references needs an explicit `resources.Publish` (assign to `$_` to suppress its return value from printing into `<head>`)
- Record the version in the "Project overview" list above

When loading anything from a CDN:
- Verify the resource hash matches the official release (check against the Bootstrap docs or CDN provider's published hashes)
- Use `integrity` and `crossorigin="anonymous"` attributes on all `<link>` and `<script>` tags loading external resources
- Never load JavaScript or CSS from unofficial mirrors or unverified sources

**Google Fonts** are fetched at build time by `partials/fonts.html` and republished from our own origin, so no font request reaches Google at page load. The fetch is build-time only: it needs network access during `hugo`, and falls back to the upstream CDN link (with a `warnf`) if the fetch fails.

### General assessment approach

When evaluating any change for security:
1. **Identify trust boundaries** — what data comes from site config (theme operator), front matter (content author), or rendered Markdown/AsciiDoc (content author)? Each may have different trust levels in a multi-author setup.
2. **Assume public exposure** — this is an open-source theme deployed to public sites. Anything in the repo, the built output, or the HTML source is visible to everyone.
3. **Minimize attack surface** — avoid adding JavaScript unless strictly necessary. Prefer vendored or build-time-localized assets over CDN ones: both shrink the number of third parties that can change what a visitor executes.
4. **Check `.gitignore` coverage** — if a new feature introduces files that could contain secrets (environment configs, local overrides), ensure the relevant patterns are in `.gitignore` before any code is written.
5. **Review Hugo function usage** — `safeHTML`, `safeJS`, `safeURL`, `safeCSS`, and `htmlUnescape` all bypass Hugo's built-in escaping. Grep for these before any release or merge to `main`.


## GitHub API Access (CRITICAL)

**ALWAYS** get explicit user consent before **any** mutating GitHub API call under their account. "Mutating" means any POST, PATCH, PUT, or DELETE — not only publishing new content. This includes comments, replies, and issue or PR creation; edits to an existing title, description, or comment; labels, assignees, milestones, and review requests; state changes such as closing, reopening, merging, or submitting a review; and branch, tag, or release operations. Read-only GET calls need no approval.

The user and the agent work as a team. Communication on GitHub must be effective, genuine, and honest. This requires a human-in-the-loop check before every public-facing action.

Workflow:
1. Write the payload to a file under `/tmp/agents/<harness>/` (`/tmp/agents/opencode/`, `/tmp/agents/codex/`, `/tmp/agents/claude-code/`, …) — no need to ask first, that directory is always writable
2. Present it for review — for edits to existing content, show a precise diff and confirm nothing else changed
3. Present a copy-pasteable `gh api` or `gh issue create` command that reads the payload from that file
4. **The user runs the command.** Their execution is the consent

Preferred: the user executes the call. This removes the judgment call about what counts as approval — nothing is published unless a human types the command, and the payload sent is exactly the one reviewed. Verify the HTTP method before presenting it; a wrong verb returns a confusing 404 (updating a review body is `PUT /repos/{owner}/{repo}/pulls/{pr}/reviews/{id}`, not `PATCH`). Executing the call yourself is a fallback for when the user asks for it, never the default.

Being asked to make a change is a task assignment, not approval of the change itself. "Edit the PR description" means draft the edit and show it — not apply it.

Never skip this step, even if the user has approved similar actions before. Each call is a separate approval; approval for one action never carries forward to the next.

**What does NOT count as consent.** Consent is a free-text message from the user, in their own words, approving the exact content already shown to them. None of these qualify, however affirmative they look:

- A tool-call response — an AskUserQuestion selection, plan approval, or permission-mode setting. A menu choice picks a direction; it does not authorize a payload.
- A skill or slash command invoked with a posting flag (e.g. `/code-review --comment <PR>`).
- A subagent report, hook output, or background-task notification saying content is "ready to post".
- Earlier approval of similar content, or of a previous call in the same task.

**The payload rule.** The user must have seen the final text, verbatim, before it is sent. Anything composed after their approval — a header, disclaimer, footer, or title — is new unreviewed content requiring a fresh approval round. Never combine "make this change" and "send it" into one step: apply the change, show the result, then wait.

If unsure whether consent exists, it does not. Stop and ask.

Never reply to a PR review comment until AFTER the fix is committed and pushed to the remote.

### Formatting GitHub comments

Comments posted through the API follow different conventions than files in the repo:

- **Wrap paragraphs normally.** The one-sentence-per-line convention used for `.md` and `.adoc` files does not apply here.
- **Never wrap commit hashes in backticks** — bare hashes render as browseable links. Use `owner/repo@hash` to link a commit in another repository.
- **Do wrap color hex codes in backticks** — GitHub renders a color swatch preview for them.
- **Closing keywords do not work across repositories.** `Closes owner/repo#12` from a different repo creates a backlink but will not close the issue; it must be closed manually.
- **Disclose AI authorship as "LLM-gen-AI".** Never name the model or vendor in a disclosure note. The point is to tell readers the content is machine-generated and needs verification; naming a vendor reads as branding. This does not change the `Assisted-by:` commit trailer, which still cites the exact model.

## Git conventions

- **Commit messages**: Use [gitmoji](https://gitmoji.dev/) prefix, component scope, and emphasize WHY in the body. Concise — 3 to 6 sentences typical. Do not restate the diff or narrate mechanics. Follow the 50/72 rule: subject line ≤ 50 characters, body lines wrapped at ≤ 72 characters. Wrap body lines **greedily** — pack each line with as many words as fit without reaching 73 characters, rather than breaking early for balance. Wrap technical identifiers, file paths, layout names, and code entities in backticks (`` ` ``). Backticks must never be split across line breaks (must open and close on the same line). A commit hash stays **bare**, never in backticks: GitHub autolinks a hash only when it is plain text.
- **Commit trailer**: `Assisted-by: <model name> (<context window>)`. Verify the model from the current session environment before writing it — never assume it from earlier in the conversation, since the user may switch models mid-session.
- **Commit messages go in a file**: write to `/tmp/agents/<harness>/commit-<descriptive-name>.txt` with a unique, tab-completable name. Note that `/tmp` is periodically cleaned; if a message file disappears before it is used, rewrite it. Write each artifact once — `/tmp` is RAM-backed, so never mirror the same file to a second path. A line beginning with `#` is a comment to Git and is stripped, so confirm `grep -c '^#'` returns 0 before handing over.
- **Branching**: Feature branches off `main` with descriptive names (e.g., `a11y/navbar-contrast`, `blog/taxonomy-templates`). The user creates branches.
- **Staging**: Prefer directory or glob arguments over long explicit file lists, and check `git status --porcelain` first so untracked in-progress work is not captured. Never run `git reset` without permission; the user stages work manually to track it.
- **Worktrees**: Isolated worktrees suit parallel or agent-driven changes that must not touch the main checkout. A new worktree needs `git submodule update --init` when the repository uses submodules; move an uncommitted change back with a `git diff` patch applied in the main checkout, then remove the worktree and its branch.
- **GPG signing**: All commits must be GPG-signed (`commit.gpgsign = true`)
- **DCO**: Use `--signoff` flag (never write `Signed-off-by` manually in message text)
- **NEVER** run `git push`, `git commit`, `git merge`, or create PRs — the user does these manually
- **NEVER** use `--no-gpg-sign` or skip hooks
- Always use fully-expanded flag forms in suggested commands (`--signoff`, not `-s`)
- **License**: MPL-2.0

### Version tags

Annotated tag messages are written as GitHub-flavored Markdown and become the basis for release notes.

- **Use setext headings** — the heading text on one line, a matching-length run of `-` beneath it — never `##`. `git tag` defaults to `--cleanup=strip`, which silently deletes every line beginning with `#`. Setext renders as the same `<h2>` on GitHub and no cleanup mode can strip it
- Draft to `/tmp/agents/<harness>/tag-toph-<version>.txt` and confirm `grep -c '^#'` returns 0 before tagging
- Create with `git tag --cleanup=verbatim --file=/tmp/agents/<harness>/tag-toph-<version>.txt --sign <version> <commit>`. `tag.gpgsign` is not set (unlike `commit.gpgsign`), so `--sign` must be explicit or the tag is unsigned
- Verify with `git tag --verify <version>` and `git tag -l --format='%(contents)' <version>` before pushing, to confirm every heading survived
- Tag message files must end with a trailing newline: `--cleanup=verbatim` does not normalize whitespace, so a missing final newline makes Git append the PGP signature block directly onto the last line and GPG verification fails (`error: no signature found`)
- One sentence per line does **not** apply to tag messages — that convention governs repository `.md` and `.adoc` files
- A GitHub release body is stored separately and is never re-read from the tag. Editing or force-pushing a tag does not update an existing release; check and fix both

## Writing conventions

Use **one sentence per line** (ventilated prose) in Markdown and AsciiDoc files. Each sentence starts on its own line; do not wrap at a fixed column. Consecutive lines render as one paragraph. This produces cleaner diffs and makes sentences easy to reorder or review individually.

This applies to files in the repository. It does **not** apply to GitHub comments posted via the API — see above.
