#!/usr/bin/env python3
"""
Build bhaktiyoga.es static site from Notion HTML exports.

Usage: python3 build.py
"""
import os
import re
import shutil
import sys
import urllib.parse

from jinja2 import Environment, FileSystemLoader

from config import (
    MAPA_DIR, TEMPLATES_DIR, OUTPUT_DIR, STATIC_DIR,
    MAIN_NAV, SITE_NAME, SITE_TAGLINE, SITE_CIF, SITE_LANG,
    SITE_URL, CONTACT_EMAIL, CONTACT_TELEGRAM, HUB_SECTIONS, FEATURED_IMAGES,
    MANUAL_CARD_COVERS, CONTENT_APPEND,
)
from slugify_pages import build_slug_map
from assets_copy import build_asset_map, copy_all_assets, copy_existing_assets, copy_static_files
from parser import parse_notion_html
from linker import rewrite_links


def _extract_notion_id_from_url(url):
    """Extract 32-char Notion ID from a relative Notion URL."""
    decoded = urllib.parse.unquote(url)
    filename = decoded.rstrip('/').split('/')[-1]
    m = re.search(r'([a-f0-9]{32})\.html$', filename)
    if m:
        return m.group(1)
    return None


def _build_cover_map(file_map, asset_map):
    """Pre-scan all pages to build {notion_id: image_url} map.

    Prefers local asset URLs; falls back to external URLs (e.g. Unsplash).
    """
    cover_map = {}
    for notion_id, file_path in file_map.items():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all cover image tags (some pages have both local and external)
        matches = re.findall(
            r'<img\s+class="page-cover-image"\s+src="([^"]+)"', content
        )
        if not matches:
            continue

        # Prefer local images over external
        local_url = None
        external_url = None
        for src in matches:
            if src.startswith('http'):
                if not external_url:
                    external_url = src.replace('&amp;', '&')
            else:
                decoded = urllib.parse.unquote(src)
                abs_img = os.path.normpath(
                    os.path.join(os.path.dirname(file_path), decoded)
                )
                rel_img = os.path.relpath(abs_img, MAPA_DIR)
                if rel_img in asset_map and not local_url:
                    local_url = asset_map[rel_img]

        if local_url:
            cover_map[notion_id] = local_url
        elif external_url:
            cover_map[notion_id] = external_url

    return cover_map


def main():
    print("=" * 60)
    print("Building bhaktiyoga.es static site")
    print("=" * 60)

    # Step 1: Clean output directory
    print("\n[1/7] Cleaning output directory...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 2: Build slug map
    print("\n[2/7] Building page slug map...")
    slug_map, file_map, title_map = build_slug_map()
    print(f"  Found {len(slug_map)} pages")

    # Step 3: Build asset map and copy assets
    print("\n[3/7] Processing assets...")
    asset_map = build_asset_map()
    print(f"  Found {len(asset_map)} media files")
    copy_all_assets(asset_map)
    copy_existing_assets()

    # Step 3b: Build cover image map for card images
    print("  Building cover image map...")
    cover_map = _build_cover_map(file_map, asset_map)
    cover_map.update(MANUAL_CARD_COVERS)
    print(f"  Found {len(cover_map)} pages with cover images")

    # Step 4: Copy static files (CSS, JS)
    print("\n[4/7] Copying static files...")
    copy_static_files()

    # Step 5: Setup Jinja2
    print("\n[5/7] Setting up templates...")
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=False,  # Content is pre-processed HTML
    )

    # Common template context
    base_context = {
        'nav_items': MAIN_NAV,
        'site_name': SITE_NAME,
        'site_tagline': SITE_TAGLINE,
        'site_cif': SITE_CIF,
        'contact_email': CONTACT_EMAIL,
        'contact_telegram': CONTACT_TELEGRAM,
    }

    # Step 6: Process and render all pages
    print("\n[6/7] Processing pages...")
    pages_built = 0
    errors = 0

    for notion_id, file_path in file_map.items():
        if notion_id not in slug_map:
            continue

        slug = slug_map[notion_id]
        title = title_map.get(notion_id, 'Sin título')

        try:
            # Read source HTML
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Parse Notion HTML
            page_data = parse_notion_html(html_content)

            # Rewrite links in content
            content = rewrite_links(
                page_data['content'],
                file_path,
                slug_map,
                asset_map,
                MAPA_DIR,
            )

            # Rewrite cover image path
            cover_image = page_data['cover_image']
            if cover_image and not cover_image.startswith('http'):
                decoded = urllib.parse.unquote(cover_image)
                abs_img = os.path.normpath(
                    os.path.join(os.path.dirname(file_path), decoded)
                )
                rel_img = os.path.relpath(abs_img, MAPA_DIR)
                if rel_img in asset_map:
                    cover_image = asset_map[rel_img]

            # Inject card images from cover_map (before URL rewrite)
            cards = page_data.get('cards', [])
            for card in cards:
                if card.get('url') and not card.get('image'):
                    card_nid = _extract_notion_id_from_url(card['url'])
                    if card_nid and card_nid in cover_map:
                        card['image'] = cover_map[card_nid]

            # Rewrite card URLs
            for card in cards:
                if card.get('url'):
                    from linker import _rewrite_href
                    new_url = _rewrite_href(
                        card['url'],
                        os.path.dirname(file_path),
                        slug_map,
                        asset_map,
                        MAPA_DIR,
                    )
                    if new_url:
                        card['url'] = new_url

            # Inject featured portrait image if configured
            if slug in FEATURED_IMAGES:
                fi = FEATURED_IMAGES[slug]
                portrait_html = (
                    f'<figure class="article-portrait">'
                    f'<img src="{fi["src"]}" alt="{fi["alt"]}" loading="lazy">'
                    f'</figure>'
                )
                content = portrait_html + content

            # Append extra content for specific pages
            if slug in CONTENT_APPEND:
                content += CONTENT_APPEND[slug]

            # Generate per-page meta description from first paragraph
            meta_description = _extract_meta_description(content)
            canonical_url = SITE_URL + slug
            og_image = cover_image if cover_image and cover_image.startswith('/') else None
            if og_image:
                og_image = SITE_URL + og_image

            # Determine current section for nav highlighting
            current_section = slug.strip('/').split('/')[0] if slug != '/' else ''

            # Build breadcrumb (only link to pages that actually exist)
            breadcrumb = _build_breadcrumb(slug, title, slug_map)

            # Choose template
            if page_data['is_hub']:
                template = env.get_template('hub.html')
            else:
                template = env.get_template('page.html')

            # Render
            rendered = template.render(
                title=page_data['title'] or title,
                content=content,
                cover_image=cover_image,
                page_type='hub' if page_data['is_hub'] else 'article',
                breadcrumb=breadcrumb,
                current_section=current_section,
                cards=cards,
                meta_description=meta_description,
                canonical_url=canonical_url,
                og_image=og_image,
                **base_context,
            )

            # Write output file
            output_path = os.path.join(OUTPUT_DIR, slug.strip('/'), 'index.html')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered)

            pages_built += 1

        except Exception as e:
            print(f"  ERROR processing {title}: {e}")
            import traceback
            traceback.print_exc()
            errors += 1

    # Step 7: Build homepage
    print("\n[7/7] Building homepage...")
    try:
        template = env.get_template('home.html')
        rendered = template.render(
            title='Inicio',
            current_section='',
            breadcrumb=[],
            cover_image=None,
            page_type='home',
            cards=[],
            content='',
            meta_description=SITE_TAGLINE,
            canonical_url=SITE_URL + '/',
            og_image=SITE_URL + '/assets/hero-bg.webp',
            **base_context,
        )
        output_path = os.path.join(OUTPUT_DIR, 'index.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered)
        pages_built += 1
    except Exception as e:
        print(f"  ERROR building homepage: {e}")
        import traceback
        traceback.print_exc()
        errors += 1

    # Step 8: Generate sitemap and robots.txt
    print("\n[8/9] Generating SEO files...")
    _generate_sitemap(slug_map)
    _generate_robots_txt()

    # Step 9: Copy English placeholder
    en_src = os.path.join(TEMPLATES_DIR, 'en_index.html')
    en_dst = os.path.join(OUTPUT_DIR, 'en', 'index.html')
    os.makedirs(os.path.dirname(en_dst), exist_ok=True)
    shutil.copy2(en_src, en_dst)

    # Summary
    print("\n" + "=" * 60)
    print(f"Build complete!")
    print(f"  Pages built: {pages_built}")
    print(f"  Errors: {errors}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    if errors > 0:
        print(f"\nWarning: {errors} errors occurred. Check output above.")

    return 0 if errors == 0 else 1


def _extract_meta_description(html_content):
    """Extract first meaningful paragraph text from HTML content for meta description."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 40:
            # Truncate to ~160 chars at word boundary
            if len(text) > 160:
                text = text[:157].rsplit(' ', 1)[0] + '...'
            return text
    return ''


def _generate_sitemap(slug_map):
    """Generate sitemap.xml from all built pages."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # Homepage
    lines.append(f'  <url><loc>{SITE_URL}/</loc><priority>1.0</priority></url>')

    for slug in sorted(slug_map.values()):
        if slug == '/' or slug == '/mapa/':
            continue
        priority = '0.8' if slug.count('/') <= 2 else '0.6'
        lines.append(f'  <url><loc>{SITE_URL}{slug}</loc><priority>{priority}</priority></url>')

    lines.append('</urlset>')

    sitemap_path = os.path.join(OUTPUT_DIR, 'sitemap.xml')
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Generated sitemap.xml ({len(slug_map) + 1} URLs)")


def _generate_robots_txt():
    """Generate robots.txt."""
    content = f"""User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
"""
    robots_path = os.path.join(OUTPUT_DIR, 'robots.txt')
    with open(robots_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  Generated robots.txt")


def _build_breadcrumb(slug, title, slug_map=None):
    """Build breadcrumb trail from a URL slug.

    Only creates clickable links for intermediate breadcrumb segments
    that correspond to real pages in slug_map.  Non-existent intermediate
    segments are emitted with url=None so the template can render them
    as plain text.
    """
    if slug == '/' or slug == '/mapa/':
        return []

    # Build set of existing page URLs for fast lookup
    existing_urls = set()
    if slug_map:
        existing_urls = set(slug_map.values())

    parts = slug.strip('/').split('/')
    breadcrumb = [('Inicio', '/')]

    # Map first part to section label
    section_labels = {
        'blog': 'Blog',
        'contenido': 'Contenido',
        'libreria': 'Librería',
        'conferencias': 'Conferencias',
        'talleres': 'Talleres',
        'eventos': 'Eventos',
        'glosario': 'Glosario',
        'videos': 'Videos',
        'revista': 'Revista',
        'curso-de-bhakti-yoga': 'Curso de Bhakti yoga',
        'la-casa-de-krsna': 'La Casa de Krsna',
        'prabhupada-now': 'Prabhupada Now!',
        'estatutos': 'Estatutos',
        'catalogo': 'Catálogo',
        'asistencia': 'Asistencia',
    }

    # Add intermediate parts
    current_path = ''
    for i, part in enumerate(parts):
        current_path += f'/{part}'
        candidate_url = current_path + '/'
        if i == len(parts) - 1:
            # Last part = current page title (always present, no link needed)
            breadcrumb.append((title, candidate_url))
        elif part in section_labels:
            # Only link if the page actually exists
            url = candidate_url if candidate_url in existing_urls else None
            breadcrumb.append((section_labels[part], url))
        else:
            label = part.replace('-', ' ').title()
            url = candidate_url if candidate_url in existing_urls else None
            breadcrumb.append((label, url))

    return breadcrumb


if __name__ == '__main__':
    sys.exit(main())
