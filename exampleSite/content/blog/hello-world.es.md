---
title: "Hola Mundo: Presentando los Blogs en Toph"
date: 2026-03-22
draft: false
categories: ["announcements"]
tags: ["toph", "blogging", "hugo"]
author: "Toph Development Team"
description: "Toph ahora es compatible con blogs. Esto es lo nuevo y cómo empezar."
---

¡Nos complace anunciar que el tema Toph de Hugo ahora es compatible con blogs!
Toph comenzó como un tema ligero de biografía y portafolio, pero se ha convertido en una plataforma de publicación capaz.
Aquí tienes un recorrido rápido por las novedades.

## Compatibilidad con taxonomías

Las publicaciones se pueden organizar con **categorías** y **etiquetas**.
Las categorías son agrupaciones amplias que se muestran como tarjetas de estilo revista en la [página de categorías](/es/categories/).
Las etiquetas son más granulares y se muestran como una nube de palabras visual en la [página de etiquetas](/es/tags/).

Para usarlas, añade `categories` y `tags` al front matter de tu publicación:

```yaml
categories: ["announcements"]
tags: ["toph", "blogging", "hugo"]
```

## Metadatos de la publicación

Cada publicación de blog muestra automáticamente su fecha de publicación, autor, tiempo de lectura y número de palabras.
Las categorías y etiquetas aparecen como insignias enlazadas debajo de la barra de metadatos.
Si tu sitio tiene `enableGitInfo: true`, aparece una fecha de "Actualizado" cuando la publicación se modifica después de su publicación.

## Archivo del blog

El [archivo del blog](/es/blog/) agrupa las publicaciones por año y mes en un diseño de acordeón colapsable.
El año y mes más recientes están expandidos de forma predeterminada, manteniendo el archivo fácil de explorar incluso a medida que crece.

## Publicaciones recientes en la página de inicio

Las cinco publicaciones de blog más recientes aparecen automáticamente en la [página de inicio](/es/).
La última publicación se destaca en una tarjeta grande, con las siguientes cuatro en una cuadrícula compacta debajo.
No se necesita configuración: si existen publicaciones de blog, aparecen.

## Navegación entre publicaciones

Al final de cada publicación, los enlaces de anterior y siguiente permiten a los lectores moverse entre publicaciones sin volver al archivo.

## Primeros pasos

Crea una nueva publicación de blog con el arquetipo integrado de Hugo:

```bash
hugo new blog/my-first-post.md
```

Esto genera una nueva publicación con los campos correctos en el front matter.
Establece `draft: false` cuando estés listo para publicar, y reconstruye tu sitio.

Para más detalles, consulta el [repositorio del tema Toph](https://github.com/justwheel/toph-hugo-theme).
