toph
====

<!--
    Style rule: one sentence per line please!
    This makes git diffs easier to read. :)
-->

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

Toph: a lightweight, responsive theme for a biography site, for use with [Hugo](https://gohugo.io/) static site generator.

> **Hugo 0.158.0 or later is required.**
> Toph uses Hugo's [`css.Build`](https://gohugo.io/functions/css/build/) function (introduced in [v0.158.0](https://github.com/gohugoio/hugo/releases/tag/v0.158.0), released March 16, 2026) to bundle modular CSS.
> Older Hugo versions will fail to build.


## Features

- Built with Bootstrap 5
- Responsive-ready
- Template-driven layout system
  - [Project profiles](#project-profiles)
  - [Dynamic footer badges](#dynamic-footer-badges)
  - [Blogging](#blogging)
- [Modular CSS architecture](#css-architecture) with customizable color palette
- First-class support for both Markdown and AsciiDoc content
- Schema.org support
- Search Engine Optimization enhancements
- [Easy customization of colors and fonts in Hugo configuration](#custom-colors-and-fonts)


## Examples

* [Official theme example website – Septima Poinsette Clark](https://justwheel.github.io/toph-hugo-theme/)
* [Justin Wheeler](https://jwheel.org)


## Installation

The recommended installation method for an existing Hugo site is with a [git submodule](https://git-scm.com/docs/git-submodule).
Use the commands below to add the theme to an existing Hugo site:

```bash
cd /path/to/hugo-site/
mkdir themes/
git submodule add git@github.com:justwheel/toph-hugo-theme.git themes/toph
git commit --signoff --message="Add Toph theme as a git submodule"
git push
```

### Update a submodule to latest upstream

Sometimes you will want to update the git submodule with new changes added upstream to this repository.
To pull newer upstream changes into your pre-existing git submodule, run the following from your Hugo project root directory:

```bash
git submodule update --remote --rebase
```

## Feature notes

### Project profiles

Toph includes a project profile feature.
Project profiles are shown on the main index page along with an image or logo.
Use these project profiles to showcase the primary content about the person, organization, or whoever/whatever the biography site is for.
The name is projects, but it can cover any type of content you wish, but you must use the correct metadata.

#### How to use

1. Create a new "projects" section.
1. Create a new AsciiDoc or Markdown file for each project profile.
1. In each profile, add the following to the front matter:
    1. `title: ""` —
     Title or name for the profile.
     This is used as the header for each profile.
    1. `date: YYYY-MM-DD` —
     Projects must have a date.
     This is used for sequencing, i.e. how the projects are ordered on the index page.
     Give older projects a date further in the past, and newer projects a date closer to the present.
     Projects will be sorted in descending order.
    1. `slug: ""` —
     Determines the anchor of the title header.
     This is handy for quick links to a specific project on the page, e.g. `example.com#project-alpha`
    1. `icon: ""` —
     Corresponding image for the project.
     The image appears in two places:
     underneath the title header, and in a carousel of images at the top of the page, underneath the index page content but before the project profiles.
    1. `hide_sitemap: true` —
     Do not add the fully-qualified link for this page to the sitemap.
     Prevents search engines from indexing "hidden" pages that are already shown as part of the site index page content.
    1. `categories: ["projects"]` —
     Required to set all project profiles to the "projects" category for the template to work.
     If the category is unset or incorrect, project profiles will not display.
1. Rebuild the site.
   The site index page now shows the project profiles.

Example of a project profile, found in `content/projects/`:

```markdown
---
title: "Open@RIT"
date: 2020-09-09
slug: open-rit
icon: /img/rit.png
hide_sitemap: true
categories: ["projects"]

---

In September 2020, I [joined][1] the Open@RIT Advisory Board.
[Open@RIT][2] is a Key Research Center of the [Rochester Institute of Technology][3] and serves as the Open Source Programs Office for RIT.
Its goals are to discover and grow RIT's impact on all things Open including, but not limited to, Open Source Software, Open Data, Open Hardware, Open Educational Resources and Creative Commons-licensed efforts.
Otherwise what we like to refer to in aggregate as _Open Work_.


[1]: https://x.com/jflory7/status/1303783881582104577
[2]: https://www.rit.edu/research/open
[3]: https://www.rit.edu/
```

### Dynamic footer badges

Toph can show affiliation or supporter badges in the footer of the site.
The footer badges are images, meant to imply an endorsement or message of support to another website or organization.
Use these to note endorsements, sponsors, or some other badge to include in the site footer.

#### How to use

1. Create a new "footers" section.
1. Create a new AsciiDoc or Markdown file for each badge.
  1. In each badge, add `categories: ["footer"]` and `hide_sitemap: true` to the front matter.
  1. Add one and _only one_ image to the file.
     Images may be wrapped by an external hyperlink.
1. Rebuild the site.
   The footer now shows the footer badges.

Example of a dynamic footer badge, found in `content/footer/`:

```asciidoc
---
categories: ["footer"]
hide_sitemap: true

---

[link=https://sfconservancy.org/sustainer/]
image::https://sfconservancy.org/img/supporter-badge.png[Become a Conservancy Sustainer!]
```

#### Badge art requirements

The height and width of all badges is fixed.
Keep in mind these requirements when adding new footer badges.

* **DPI**:
  25.40 dpi
* **Height**:
  90 pixels
* **Width**:
  194 pixels
* **Style suggestions**:
  * Add a light-gray (RGBA: `#272b35ff`) border around the badge.

### Blogging

Toph includes a full-featured blogging system with taxonomy support, pagination, and content discovery.

#### Key features

- **Blog archive** — posts grouped by year and month in a collapsible accordion at `/blog/`
- **Categories** — magazine-style card grid with images, descriptions, and recent posts at `/categories/`
- **Tags** — visual word cloud with font-size/opacity scaling by post count at `/tags/`
- **Post metadata** — publication date, author, reading time, word count, and taxonomy badges
- **Post navigation** — previous/next links at the bottom of each post
- **Recent posts** — the 5 most recent posts displayed on the homepage
- **Cover images** — optional `coverImage` front matter for a featured image on each post
- **Image captions** — `![alt](src "caption")` renders as `<figure>/<figcaption>`
- **Heading anchors** — clickable 🔗 links on section headings for sharing direct URLs
- **Pagination** — configurable page size via `pagination.pagerSize` in config
- **Configurable date format** — set `params.date_format` to any [Go time format](https://gohugo.io/functions/time/format/) (default: `"2006 January 02"`)
- **Configurable footer license** — set `params.legal.license` with `name`, `url`, and `title` fields
- **RSS feed** — custom RSS template with full post content
- **AsciiDoc support** — all features work identically for both Markdown and AsciiDoc content

#### Creating a blog post

```bash
hugo new blog/my-first-post.md
```

This uses the `blog.md` archetype which scaffolds the standard front matter fields.
Set `draft: false` when ready to publish.

#### Configuration

Add the following to your Hugo configuration to enable taxonomy filtering and pagination:

```yaml
taxonomies:
  category: categories
  tag: tags

pagination:
  pagerSize: 10

params:
  taxonomy_exclude: ["footer", "projects"]
  layouts:
    categories:
      recent_posts: 3
      excerpt_length: 250
```

### CSS architecture

Toph uses Hugo's `css.Build` function to bundle modular CSS files into a single stylesheet at build time.
The source CSS is organized under `assets/css/` in four directories:

```
assets/css/
  main.css                 @import entrypoint (no rules, only imports)
  base/                    Variables, global styles, navbar, main content area
  components/              Cover image, hero, post metadata, post nav, code blocks, footer
  taxonomy/                Sort controls, term excerpts, categories grid, tags word cloud
  blog/                    Recent posts, blog archive accordion
```

All neutral/utility colors (text, borders, backgrounds, shadows) are defined as CSS custom properties in `base/_variables.css`.
Brand colors (`--primary`, `--secondary`, `--accent-color`) and fonts are set from Hugo config via an inline `<style>` block in `head.html`.
Both sets of variables coexist on `:root` without conflict.

To add new CSS for a new component, create a new `_component-name.css` file in the appropriate directory and add an `@import` line to `main.css`.

### Custom colors and fonts

Toph supports quick and easy customization of colors and fonts in the Hugo config file.
The site features three colors and three fonts used across all layouts:

* **Colors**:
  * Primary:
    Dominant color used across all layouts in highly visible locations.
  * Secondary:
    Background or secondary color.
    Most notable use in background color of all pages.
  * Accent:
    Color to accent or emphasize content in contrast to the primary color.
* **Fonts**:
  * Default:
    Used as typeface for almost all content across the site.
  * Title:
    Used in page titles only.
  * Header:
    Used in all headers other than the page title.

#### How to use

Include the following in your Hugo configuration file:

**YAML**:

```yaml
params:
  colors:
    primary: darkorchid
    secondary: linen
    accent: darkslateblue
  fonts:
    default: Open Sans
    title: Bungee Shade
    header: Roboto Slab
```

**TOML**:

```toml
[params.colors]
primary = "darkorchid"
secondary = "linen"
accent = "darkslateblue"

[params.fonts]
default = "Open Sans"
title = "Bungee Shade"
header = "Roboto Slab"
```


## Contributing

There are a few ways to contribute to this theme.

### Share feedback

[Open a new issue to report bugs and request new features.](https://github.com/justwheel/toph-hugo-theme/issues/new)

### Contribute code

Fork and clone this repository.
Then, open a Pull Request when you have changes to propose.


## Legal

Licensed under the [Mozilla Public License 2.0](https://www.mozilla.org/en-US/MPL/ "About the Mozilla Public License") (MPL-2.0).
From [_choosealicense.com_](https://choosealicense.com/licenses/mpl-2.0/):

> Permissions of this weak copyleft license are conditioned on making available source code of licensed files and modifications of those files under the same license (or in certain cases, one of the GNU licenses).
> Copyright and license notices must be preserved.
> Contributors provide an express grant of patent rights.
> However, a larger work using the licensed work may be distributed under different terms and without source code for files added in the larger work.
