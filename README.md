# mega-bite
MEGA BITE - Tech News, AI Tools and Technology Updates

A fast, dependency-free static website: no build step, no framework.

## Features

- Home page with featured story, category filters and live search
- Article pages (`#/post/<id>`), an **AI Tools** page and an **About** page
- Responsive layout (checked down to 320px wide)
- Light / dark theme (follows the system, with a manual toggle)

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

(Any static file server works. Opening `index.html` directly also works.)

## Add or edit content

All content lives in `assets/data.js`. The articles currently in it are **placeholder demo content**: replace them with your own.

Each article looks like this:

```js
{
  id: "my-first-post",          // used in the URL: #/post/my-first-post
  title: "My first post",
  summary: "One or two sentences shown on the card.",
  category: "Tech News",        // must be one of `categories`
  date: "2026-11-15",
  minutes: 3,
  body: ["First paragraph.", "Second paragraph."]
}
```

Once you have real articles, remove the "Demo content" notice from `index.html`.

## Deploy

It is plain static files, so it can be hosted anywhere: GitHub Pages, Netlify, Cloudflare Pages, or any web server. Point your domain at the host and upload this folder's contents.

## Structure

```
index.html          page shell
assets/styles.css   styling (light/dark tokens)
assets/data.js      site content
assets/app.js       routing + rendering
assets/favicon.svg  icon
```
