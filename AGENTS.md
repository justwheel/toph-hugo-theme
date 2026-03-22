# AGENTS.md

This file provides guidance to AI agents (including Claude Code) when working with code in this repository.


## Project overview

Toph is a lightweight, responsive Hugo theme for biography and portfolio sites, built on Bootstrap 5.3 (CDN) and licensed MPL-2.0. It features project profiles, dynamic footer badges, a data-driven social media system, blogging with taxonomy support, and Schema.org SEO.

- **Hugo minimum version**: 0.123.0 (CI uses 0.158.0 Extended)
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

The GitHub Actions workflow (`.github/workflows/hugo.yml`) runs on PRs and pushes to `main`:

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
| `footer.html` | Footer badges + footer-box (copyright, CC BY-SA 4.0, repo link) |
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

All styles live in `assets/css/main.css`, processed by Hugo Pipes (minify + fingerprint). Colors and fonts are injected as CSS custom properties from `params.colors` and `params.fonts` in the site config via `head.html`.

Key specificity pattern: `main a { color: #003366 }` (specificity 0,0,1,1) overrides bare class selectors on `<a>` elements inside `<main>`. Badge and link classes that need their own color must be prefixed with `main a.classname` (specificity 0,0,2,1) to win.

### Structural vs. blog content

`single.html` uses guards to distinguish structural content (projects, footer badges) from blog posts:
- **`$is_structural`**: pages whose categories overlap with `params.taxonomy_exclude` or have `hide_sitemap: true`
- **`$is_blog_post`**: non-structural pages with a publication date

Blog features (post-meta, post-nav, ToC) only render for blog posts.

### Render hooks

- `_default/_markup/render-heading.html` — Adds anchor links to Markdown headings (AsciiDoc headings are post-processed with `replaceRE` in `single.html`)

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


## Git conventions

- **Commit messages**: Use [gitmoji](https://gitmoji.dev/) prefix, component scope, and emphasize WHY in the body
- **Commit trailer**: `Assisted-by: <model name>` per Fedora AI-Assisted Contributions Policy
- **Branching**: Feature branches off `main` with descriptive names (e.g., `a11y/navbar-contrast`, `blog/taxonomy-templates`)
- **GPG signing**: All commits must be GPG-signed (`commit.gpgsign = true`)
- **DCO**: Use `--signoff` flag (never write `Signed-off-by` manually in message text)
- **License**: MPL-2.0
