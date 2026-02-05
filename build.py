#!/usr/bin/env python3
"""
Build bhaktiyoga.es static site from Notion HTML exports.

Usage: python3 build.py
"""
import os
import shutil
import sys

from jinja2 import Environment, FileSystemLoader

from config import (
    MAPA_DIR, TEMPLATES_DIR, OUTPUT_DIR, STATIC_DIR,
    MAIN_NAV, SITE_NAME, SITE_TAGLINE, SITE_CIF, SITE_LANG,
    CONTACT_EMAIL, CONTACT_TELEGRAM, HUB_SECTIONS, FEATURED_IMAGES,
)
from slugify_pages import build_slug_map
from assets_copy import build_asset_map, copy_all_assets, copy_existing_assets, copy_static_files
from parser import parse_notion_html
from linker import rewrite_links


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
                import urllib.parse
                decoded = urllib.parse.unquote(cover_image)
                abs_img = os.path.normpath(
                    os.path.join(os.path.dirname(file_path), decoded)
                )
                rel_img = os.path.relpath(abs_img, MAPA_DIR)
                if rel_img in asset_map:
                    cover_image = asset_map[rel_img]

            # Rewrite card URLs
            cards = page_data.get('cards', [])
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

            # Determine current section for nav highlighting
            current_section = slug.strip('/').split('/')[0] if slug != '/' else ''

            # Build breadcrumb
            breadcrumb = _build_breadcrumb(slug, title)

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

    # Step 8: Copy English placeholder
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


def _build_breadcrumb(slug, title):
    """Build breadcrumb trail from a URL slug."""
    if slug == '/' or slug == '/mapa/':
        return []

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
        if i == len(parts) - 1:
            # Last part = current page title
            breadcrumb.append((title, current_path + '/'))
        elif part in section_labels:
            breadcrumb.append((section_labels[part], current_path + '/'))
        else:
            # Use the slug as label (capitalize)
            label = part.replace('-', ' ').title()
            breadcrumb.append((label, current_path + '/'))

    return breadcrumb


if __name__ == '__main__':
    sys.exit(main())
