# bhaktiyoga.es Static Site

## Project Structure

- `output/` — Final website (deployed to Cloudflare). Rebuilt fresh every `python3 build.py`
- `templates/` — Jinja2 HTML templates (home.html, base.html, page.html, hub.html)
- `static/` — CSS, JS, favicon
- `existing_assets/` — Manually added images (temple.jpg, hero-bg.webp, etc.)
- `notion_full/` — Original Notion HTML export (source content)
- `build.py` — Main build orchestrator
- `config.py` — Paths, nav structure, constants
- `parser.py` — Notion HTML content extraction (BeautifulSoup)
- `slugify_pages.py` — Filename to slug mapping
- `linker.py` — Link rewriting
- `assets_copy.py` — Media file processing

## How to Update and Deploy

1. Make changes to templates, CSS, or config
2. Build: `python3 build.py`
3. Deploy: `npx wrangler pages deploy output/ --project-name=bhaktiyoga-es --branch=master`

**Important:** Always use `--branch=master` when deploying, otherwise it goes to Preview instead of Production.

## Cloudflare Pages

- Project name: `bhaktiyoga-es`
- Production branch: `master` (local git uses `main`)
- Custom domains: `bhaktiyoga.es`, `www.bhaktiyoga.es`
- To fix the branch mismatch: Cloudflare dashboard > Pages > bhaktiyoga-es > Settings > Builds & deployments > Change production branch from `master` to `main`

## Homepage

The homepage (`templates/home.html`) is a standalone page replicating the original Mobirise design. It does NOT extend `base.html`. It uses Bootstrap 5 from CDN and Jost font from Google Fonts.

## Key Technical Notes

- Notion HTML exports have ~375 lines of CSS before body content. Always read entire files, not just first 8KB
- Cover images are only in individual page `<header>` as `<img class="page-cover-image">`, NOT in collection tables
- Card URL rewriting must happen AFTER image injection (needs raw Notion URLs to extract notion_ids)
- `MANUAL_CARD_COVERS` in config.py for pages without Notion cover images
- `CONTENT_APPEND` in config.py to inject extra HTML into specific pages
