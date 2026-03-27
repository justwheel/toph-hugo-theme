# AGENTS.md

This file provides guidance to AI agents (including Claude Code) when working with code in this repository.


## Project overview

Toph is a lightweight, responsive Hugo theme for biography and portfolio sites, built on Bootstrap 5.3 (CDN) and licensed MPL-2.0. It features project profiles, dynamic footer badges, a data-driven social media system, blogging with taxonomy support, and Schema.org SEO.

- **Hugo minimum version**: 0.158.0 Extended (required for `css.Build`)
- **Bootstrap**: 5.3.8 via CDN (not vendored)
- **Bootstrap Icons**: 1.11.3 via CDN
- **Content formats**: Markdown and AsciiDoc (via Asciidoctor)
- **Example site**: `exampleSite/` — deployed to GitHub Pages as a live demo


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
  index.html         Homepage: hero, for-hire, content, recent-posts, projects
  _default/
    list.html        Paginated content list with excerpts
    single.html      Single page with blog guards ($is_structural, $is_blog_post)
    terms.html       Fallback taxonomy terms list with sort toggle
    term.html        Fallback single term page with pagination
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
| `projects.html` | Project profiles with icons |
| `projects-carousel.html` | Image carousel above projects |
| `for-hire.html` | Optional hire-me banner |

### Data-driven social media

Social platforms are defined in `data/social.yaml` as a registry of 11 platforms, each with a `name`, `url` template (using `%s` for the username), and Bootstrap `icon` class. Site config references platforms by registry key (e.g., `social.github: "username"`). The nav partial and hero partial both look up platforms via `$.Site.Data.social`.

Config keys in `params.social` **must match** `data/social.yaml` keys exactly. Mismatched keys silently produce no output.

The LinkedIn URL template is generic (`.../%s`) to support both personal (`in/user`) and company (`company/name`) profiles. Mastodon uses `%s` directly (expects a full URL).

### CSS architecture

Styles are processed by Hugo's `css.Build` function (requires Hugo 0.158.0+), which resolves `@import` statements into a single output file at build time. The template in `head.html` uses:

```go-html-template
{{- $css := resources.Get "css/main.css" | css.Build | fingerprint }}
```

#### File structure

```
assets/css/
  main.css                        @import entrypoint (no CSS rules)
  base/
    _variables.css                :root custom properties (neutral palette)
    _global.css                   Body, headings, anchor links
    _nav.css                      Fixed navbar, dropdowns, hover states
    _content.css                  Main body: links, images, figures, ToC, profile
  components/
    _cover.css                    Cover image for blog posts
    _hero.css                     Homepage hero section
    _post-meta.css                Blog post metadata bar
    _post-nav.css                 Prev/next post navigation
    _code.css                     Code block borders
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
4. **All color values must use CSS custom properties** — never hardcode hex values, `rgba()`, or named colors outside of `base/_variables.css`. Define new variables in `_variables.css` and reference them with `var()`.
5. **Brand colors** (`--primary`, `--secondary`, `--accent-color`) and font variables are injected via inline `<style>` in `head.html` from Hugo site config. These cannot be defined in CSS files. The neutral palette in `_variables.css` coexists on `:root` without conflict.
6. **Underscore prefix convention**: partial filenames start with `_` to signal they are not standalone stylesheets.

#### Key specificity pattern

`main a { color: var(--text-link) }` (specificity 0,0,1,1) overrides bare class selectors on `<a>` elements inside `<main>`. Badge and link classes that need their own color must be prefixed with `main a.classname` (specificity 0,0,2,1) to win.

### Structural vs. blog content

`single.html` uses guards to distinguish structural content (projects, footer badges) from blog posts:
- **`$is_structural`**: pages whose categories overlap with `params.taxonomy_exclude` or have `hide_sitemap: true`
- **`$is_blog_post`**: non-structural pages with a publication date

Blog features (post-meta, post-nav, ToC) only render for blog posts.

### Render hooks

- `_default/_markup/render-heading.html` — Adds anchor links to Markdown headings (AsciiDoc headings are post-processed with `replaceRE` in `single.html`)
- `_default/_markup/render-image.html` — Wraps images in `<figure>/<figcaption>` when a title is provided

### i18n

Translation files in `i18n/`: `en.yaml`, `es.yaml`, `ar.yaml`, `hi.yaml`. Arabic and Spanish are disabled in the example site config; Hindi has a translation file but is not configured. Key namespaces: `404_page`, `footer`, `hire_me`, `index`, `hero`, `misc`.

### Archetypes

- `default.md` — Generic content
- `blog.md` — Blog post with title, date, draft, categories, tags, author, description


## WCAG AA accessibility

This project enforces WCAG AA contrast ratios via Pa11y CI:
- **4.5:1** for normal text, **3:1** for large text
- Minimum accessible gray on white background: `#767676` (4.54:1)
- All muted text uses `#767676`; never use `#888` or lighter grays
- Chroma syntax highlighting theme is `github` (passes WCAG AA; `monokai` does not)
- Navbar dropdowns are hover-triggered (no `data-bs-toggle="dropdown"`) using the `.nav-hover-dropdown` class — all dropdowns must use this pattern
- Bootstrap `.dropdown-item` defaults to dark text — must override `color: var(--secondary)` for colored dropdown backgrounds


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


## Git conventions

- **Commit messages**: Use [gitmoji](https://gitmoji.dev/) prefix, component scope, and emphasize WHY in the body
- **Commit trailer**: `Assisted-by: <model name>` per Fedora AI-Assisted Contributions Policy
- **Branching**: Feature branches off `main` with descriptive names (e.g., `a11y/navbar-contrast`, `blog/taxonomy-templates`)
- **GPG signing**: All commits must be GPG-signed (`commit.gpgsign = true`)
- **DCO**: Use `--signoff` flag (never write `Signed-off-by` manually in message text)
- **License**: MPL-2.0
