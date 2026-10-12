# bhaktiyoga.es — generador del sitio estático

Generador en Python del sitio estático de bhaktiyoga.es («Centros de Bhakti yoga»). Toma una exportación HTML de Notion, extrae el contenido, reescribe enlaces e imágenes y lo vuelca en plantillas Jinja2. El resultado va a `output/` y se publica en Cloudflare Pages.

## Estructura

- `build.py` — orquestador del build; borra y regenera `output/`, con `sitemap.xml` y `robots.txt`.
- `config.py` — rutas, navegación, datos del sitio y ajustes manuales (`MANUAL_CARD_COVERS`, `CONTENT_APPEND`…).
- `parser.py` — extrae el contenido de los HTML de Notion (BeautifulSoup).
- `slugify_pages.py` — mapea nombres de fichero a slugs.
- `linker.py` — reescritura de enlaces.
- `assets_copy.py` — copia y procesa imágenes y otros medios.
- `check_broken_links.py` — busca enlaces internos rotos en `output/`.
- `templates/` — plantillas Jinja2 (`base.html`, `home.html`, `page.html`, `hub.html`, `en_index.html`).
- `static/` — CSS, JS (`nav.js`), fuentes y favicon.
- `existing_assets/` — imágenes añadidas a mano.
- `original_index.html` — portada original hecha con Mobirise, de referencia.
- `notion_full/` y `output/` — exportación de Notion y sitio generado; ambos ignorados por git y ausentes ahora mismo en la carpeta.

## Uso

```
python3 build.py
python3 check_broken_links.py
npx wrangler pages deploy output/ --project-name=bhaktiyoga-es --branch=master
```

Usar siempre `--branch=master`: sin él el despliegue va a Preview y no a producción (el git local usa `main`). Dominios: `bhaktiyoga.es` y `www.bhaktiyoga.es`.

El build necesita `notion_full/` en su sitio (ruta en `config.py`).

## Estado

- Primer commit el 5-feb-2026; rediseño del footer el 6-feb-2026.
- «Sync before machine transfer» (22-mar-2026).
- Último commit: checkpoint del 16-jun-2026 (imágenes de `existing_assets/`).

## Repositorio

`https://github.com/juanmanuelferrera/trasladar_bhaktiyoga_web.git`
