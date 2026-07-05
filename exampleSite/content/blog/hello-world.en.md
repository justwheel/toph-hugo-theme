---
title: "Hello World: Introducing Blogging in Toph"
date: 2026-03-22
draft: false
categories: ["announcements"]
tags: ["toph", "blogging", "hugo"]
author: "Toph Development Team"
description: "Toph now supports blogging. Here's what's new and how to get started."
---

We're excited to announce that the Toph Hugo theme now supports blogging!
Toph started as a lightweight biography and portfolio theme, but it has grown into a capable publishing platform.
Here's a quick tour of what's new.

## Taxonomy support

Posts can be organized with **categories** and **tags**.
Categories are broad groupings displayed as magazine-style cards on the [categories page](/categories/).
Tags are more granular and shown as a visual word cloud on the [tags page](/tags/).

To use them, add `categories` and `tags` to your post's front matter:

```yaml
categories: ["announcements"]
tags: ["toph", "blogging", "hugo"]
```

## Post metadata

Every blog post automatically displays its publication date, author, reading time, and word count.
Categories and tags appear as linked badges beneath the metadata bar.
If your site has `enableGitInfo: true`, an "Updated" date appears when the post is modified after publication.

## Blog archive

The [blog archive](/blog/) groups posts by year and month in a collapsible accordion layout.
The most recent year and month are expanded by default, keeping the archive scannable even as it grows.

## Recent posts on the homepage

The five most recent blog posts appear on the [homepage](/) automatically.
The latest post is featured in a large card, with the next four in a compact grid below it.
No configuration is needed — if blog posts exist, they show up.

## Post navigation

At the bottom of each post, previous and next links let readers move between posts without going back to the archive.

## Getting started

Create a new blog post with Hugo's built-in archetype:

```bash
hugo new blog/my-first-post.md
```

This scaffolds a new post with the right front matter fields.
Set `draft: false` when you're ready to publish, and rebuild your site.

For more details, see the [Toph theme repository](https://github.com/justwheel/toph-hugo-theme).
