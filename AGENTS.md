# AGENTS.md

This file provides guidance to AI agents (including Claude Code) when working with code in this repository.


## Project overview

Toph is a lightweight, responsive Hugo theme for biography and portfolio sites, built on Bootstrap 5.3 (CDN) and licensed MPL-2.0. It features project profiles, dynamic footer badges, a data-driven social media system, blogging with taxonomy support, and Schema.org SEO.

- **Hugo minimum version**: 0.161.0 Extended (required for `css.Build` with nested `vars`)
- **Bootstrap**: 5.3.8 via CDN (not vendored)
- **Bootstrap Icons**: 1.11.3 via CDN
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
3. **Rebuilds with `--baseURL http://localhost:3000/`** for Pa11y (critical — without this, Chromium fetches stale CSS from the deployed site instead of freshly built assets)
4. Runs Pa11y accessibility audit against all sitemap URLs
5. Rebuilds again with the Pages baseURL for the deployment artifact
6. Deploys to GitHub Pages (only on `main`)

CI tools live in `.github/package.json` (pa11y-ci, serve). Install with `npm ci --prefix .github`.

**Pa11y accessibility rules**: Only errors fail the build (`includeWarnings` is OFF). HTMLCS transparency checks (G18.Abs) are warnings, not errors.


## Architecture

### Layout hierarchy

```
baseof.html          HTML skeleton: head, nav, header, <main>, footer
  index.html         Homepage: hero, for-hire, content, recent-posts, projects, team
  _default/
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

### Key partials

| Partial | Purpose |
|---------|---------|
| `head.html` | Meta, CSS variables from config, CDN links (Bootstrap, Icons, Google Fonts) |
| `nav.html` | Fixed navbar with hover-triggered dropdowns, social links from data registry, translation selector |
| `hero.html` | Compact centered hero: profile photo, tagline, social icons, about link |
| `header.html` | Page title (`biography.name` on home, `.Title` elsewhere) |
| `footer.html` | Footer badges + footer-box (configurable license, repo link) |
| `seo-meta.html` | Schema.org Person JSON-LD, OpenGraph, Twitter cards |
| `pagination.html` | Bootstrap 5 pagination with i18n and ARIA labels |
| `post-meta.html` | Date, updated, author, reading time, word count, taxonomy badges |
| `post-nav.html` | Prev/next post navigation within section |
| `recent-posts.html` | Homepage: 1 featured + 4 secondary cards with stretched links |
| `resolve-image-path.html` | Shared image path resolution: handles remote URLs (https://), protocol-relative (//), absolute (/path), and relative (filename) paths |
| `projects.html` | Project profiles with icons |
| `projects-carousel.html` | Image carousel above projects |
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
  components/
    _cover.css                    Cover image for blog posts
    _hero.css                     Homepage hero section
    _post-meta.css                Blog post metadata bar
    _post-nav.css                 Prev/next post navigation
    _asciidoc-admonition.css      AsciiDoc admonition blocks (note, tip, warning…)
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

- `_default/_markup/render-heading.html` — Adds anchor links to Markdown headings (AsciiDoc headings are post-processed with `replaceRE` in `single.html`)
- `_default/_markup/render-image.html` — Wraps images in `<figure>/<figcaption>` when a title is provided
- `partials/resolve-image-path.html` — Shared image path resolution used by both `single.html` (cover images) and `rss.xml` (feed images). Accepts `dict "src" $src "file" .File` and returns the resolved path. Handles remote URLs (`https://`), protocol-relative URLs (`//`), absolute paths (`/path`), and relative filenames (resolved via `.File`).

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

Translation files in `i18n/`: `en.yaml`, `es.yaml`, `ar.yaml`, `hi.yaml`. Arabic and Spanish are disabled in the example site config; Hindi has a translation file but is not configured. Key namespaces: `404_page`, `footer`, `hire_me`, `index`, `hero`, `misc`.

### Archetypes

- `default.md` — Generic content
- `blog.md` — Blog post with title, date, draft, categories, tags, author, description


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

Headless Chrome defaults to `prefers-color-scheme: dark`, so a default Pa11y run exercises **dark mode**, not light. To test a specific mode, emulate it explicitly. To reproduce the no-JS path, disable JavaScript *and* emulate dark — the bug class above is invisible with JavaScript on.


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

Bootstrap and Bootstrap Icons are loaded via CDN. When updating CDN URLs:
- Verify the resource hash matches the official release (check against the Bootstrap docs or CDN provider's published hashes)
- Use `integrity` and `crossorigin="anonymous"` attributes on all `<link>` and `<script>` tags loading external resources
- Never load JavaScript or CSS from unofficial mirrors or unverified sources

### General assessment approach

When evaluating any change for security:
1. **Identify trust boundaries** — what data comes from site config (theme operator), front matter (content author), or rendered Markdown/AsciiDoc (content author)? Each may have different trust levels in a multi-author setup.
2. **Assume public exposure** — this is an open-source theme deployed to public sites. Anything in the repo, the built output, or the HTML source is visible to everyone.
3. **Minimize attack surface** — avoid adding JavaScript unless strictly necessary. Static HTML with CDN resources has a small attack surface; keep it that way.
4. **Check `.gitignore` coverage** — if a new feature introduces files that could contain secrets (environment configs, local overrides), ensure the relevant patterns are in `.gitignore` before any code is written.
5. **Review Hugo function usage** — `safeHTML`, `safeJS`, `safeURL`, `safeCSS`, and `htmlUnescape` all bypass Hugo's built-in escaping. Grep for these before any release or merge to `main`.


## GitHub API access (CRITICAL)

**ALWAYS** get explicit user consent before **any** mutating GitHub API call under their account. "Mutating" means any POST, PATCH, PUT, or DELETE — not only publishing new content. This includes comments, replies, and issue or PR creation; edits to an existing title, description, or comment; labels, assignees, milestones, and review requests; state changes such as closing, reopening, merging, or submitting a review; and branch, tag, or release operations. Read-only GET calls need no approval.

The user and the agent work as a team. Communication on GitHub must be effective, genuine, and honest. This requires a human-in-the-loop check before every public-facing action.

Workflow:
1. Write the payload to a file under `/tmp` — no need to ask first, `/tmp` is always writable
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

- **Commit messages**: Use [gitmoji](https://gitmoji.dev/) prefix, component scope, and emphasize WHY in the body. Concise — 3 to 6 sentences typical. Do not restate the diff or narrate mechanics.
- **Commit trailer**: `Assisted-by: <model name> (<context window>)`. Verify the model from the current session environment before writing it — never assume it from earlier in the conversation, since the user may switch models mid-session.
- **Commit messages go in a file**: write to `/tmp/commit-<descriptive-name>.txt` with a unique, tab-completable name. Note that `/tmp` is periodically cleaned; if a message file disappears before it is used, rewrite it.
- **Branching**: Feature branches off `main` with descriptive names (e.g., `a11y/navbar-contrast`, `blog/taxonomy-templates`). The user creates branches.
- **GPG signing**: All commits must be GPG-signed (`commit.gpgsign = true`)
- **DCO**: Use `--signoff` flag (never write `Signed-off-by` manually in message text)
- **NEVER** run `git push`, `git commit`, or create PRs — the user does these manually
- **NEVER** use `--no-gpg-sign` or skip hooks
- Always use fully-expanded flag forms in suggested commands (`--signoff`, not `-s`)
- **License**: MPL-2.0

### Version tags

Annotated tag messages are written as GitHub-flavored Markdown and become the basis for release notes.

- **Use setext headings** — the heading text on one line, a matching-length run of `-` beneath it — never `##`. `git tag` defaults to `--cleanup=strip`, which silently deletes every line beginning with `#`. Setext renders as the same `<h2>` on GitHub and no cleanup mode can strip it
- Draft to `/tmp/tag-toph-<version>.txt` and confirm `grep -c '^#'` returns 0 before tagging
- Create with `git tag --cleanup=verbatim --file=/tmp/tag-toph-<version>.txt --sign <version> <commit>`. `tag.gpgsign` is not set (unlike `commit.gpgsign`), so `--sign` must be explicit or the tag is unsigned
- Verify with `git tag --verify <version>` and `git tag -l --format='%(contents)' <version>` before pushing, to confirm every heading survived
- One sentence per line does **not** apply to tag messages — that convention governs repository `.md` and `.adoc` files
- A GitHub release body is stored separately and is never re-read from the tag. Editing or force-pushing a tag does not update an existing release; check and fix both

## Writing conventions

Use **one sentence per line** (ventilated prose) in Markdown and AsciiDoc files. Each sentence starts on its own line; do not wrap at a fixed column. Consecutive lines render as one paragraph. This produces cleaner diffs and makes sentences easy to reorder or review individually.

This applies to files in the repository. It does **not** apply to GitHub comments posted via the API — see above.
