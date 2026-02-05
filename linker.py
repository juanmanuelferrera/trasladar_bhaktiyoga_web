"""Rewrite internal links from Notion format to clean URLs."""
import os
import re
import shutil
import urllib.parse
from bs4 import BeautifulSoup
from slugify import slugify as _slugify

from slugify_pages import NOTION_FILENAME_RE
from config import SLUG_OVERRIDES, NOTION_EXPORT_DIR, OUTPUT_DIR


def rewrite_links(html_content, source_file_path, slug_map, asset_map, mapa_dir):
    """
    Rewrite all links and image sources in HTML content.

    Args:
        html_content: HTML string with Notion-style links
        source_file_path: absolute path of the source HTML file
        slug_map: {notion_id: clean_url}
        asset_map: {relative_path: /assets/clean-name.ext}
        mapa_dir: absolute path to Mapa de la web directory

    Returns:
        Rewritten HTML string
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    source_dir = os.path.dirname(source_file_path)

    # Rewrite <a href="...">
    for a in soup.find_all('a', href=True):
        href = a['href']
        new_href = _rewrite_href(href, source_dir, slug_map, asset_map, mapa_dir)
        if new_href:
            a['href'] = new_href

    # Rewrite <img src="...">
    for img in soup.find_all('img', src=True):
        src = img['src']
        new_src = _rewrite_asset_src(src, source_dir, asset_map, mapa_dir)
        if new_src:
            img['src'] = new_src

    # Rewrite background-image in style attributes
    for tag in soup.find_all(style=re.compile(r'background-image')):
        style = tag['style']
        urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
        for url in urls:
            new_url = _rewrite_asset_src(url, source_dir, asset_map, mapa_dir)
            if new_url:
                style = style.replace(url, new_url)
        tag['style'] = style

    return str(soup)


def _rewrite_href(href, source_dir, slug_map, asset_map, mapa_dir):
    """Rewrite a single href value."""
    # Skip anchors and javascript
    if href.startswith('#') or href.startswith('javascript:'):
        return None

    # Decode URL encoding
    decoded = urllib.parse.unquote(href)

    # Handle external links
    if decoded.startswith('http://') or decoded.startswith('https://'):
        # bhakti.pages.dev -> homepage
        if 'bhakti.pages.dev' in decoded:
            return '/'
        # notion.so links -> try to extract ID and map
        if 'notion.so' in decoded or 'notion.site' in decoded:
            notion_id = _extract_notion_id_from_url(decoded)
            if notion_id and notion_id in slug_map:
                return slug_map[notion_id]
        # Keep other external links
        return None

    # Handle relative links to HTML pages
    if decoded.endswith('.html') or '.html#' in decoded:
        # Split off any anchor
        anchor = ''
        if '#' in decoded:
            decoded, anchor = decoded.rsplit('#', 1)
            anchor = '#' + anchor

        # Resolve the relative path
        abs_path = os.path.normpath(os.path.join(source_dir, decoded))

        # Extract Notion ID from the resolved filename
        filename = os.path.basename(abs_path)
        m = NOTION_FILENAME_RE.match(filename)
        if m:
            notion_id = m.group(2)
            if notion_id in slug_map:
                return slug_map[notion_id] + anchor
            # Fallback: check SLUG_OVERRIDES for pages outside MAPA_DIR
            if notion_id in SLUG_OVERRIDES:
                return SLUG_OVERRIDES[notion_id] + anchor

        # Try getting ID from the href itself (before resolution)
        basename = os.path.basename(decoded)
        m = NOTION_FILENAME_RE.match(basename)
        if m:
            notion_id = m.group(2)
            if notion_id in slug_map:
                return slug_map[notion_id] + anchor
            if notion_id in SLUG_OVERRIDES:
                return SLUG_OVERRIDES[notion_id] + anchor

        return None

    # Handle relative links to non-HTML files (assets)
    return _rewrite_asset_src(href, source_dir, asset_map, mapa_dir)


def _rewrite_asset_src(src, source_dir, asset_map, mapa_dir):
    """Rewrite an asset source path."""
    # Skip data URIs
    if src.startswith('data:'):
        return None

    # Keep external URLs as-is
    if src.startswith('http://') or src.startswith('https://'):
        # Notion icons -> skip (we'll use CSS)
        if 'notion.so/icons' in src:
            return None
        return None

    # Decode
    decoded = urllib.parse.unquote(src)

    # Resolve relative path
    abs_path = os.path.normpath(os.path.join(source_dir, decoded))
    rel_to_mapa = os.path.relpath(abs_path, mapa_dir)

    # Look up in asset map
    if rel_to_mapa in asset_map:
        return asset_map[rel_to_mapa]

    # Try with different path separators
    rel_normalized = rel_to_mapa.replace('\\', '/')
    if rel_normalized in asset_map:
        return asset_map[rel_normalized]

    # Try matching just the filename
    basename = os.path.basename(decoded)
    for orig_path, clean_path in asset_map.items():
        if os.path.basename(orig_path) == basename:
            return clean_path

    # Handle out-of-tree assets: file exists in the broader Notion export
    # but outside MAPA_DIR (e.g. "Copy of Conocimiento/" sibling dirs)
    if rel_to_mapa.startswith('..') and os.path.isfile(abs_path):
        rel_to_export = os.path.relpath(abs_path, NOTION_EXPORT_DIR)
        if not rel_to_export.startswith('..'):
            name_no_ext, ext = os.path.splitext(basename)
            clean_name = _slugify(name_no_ext, lowercase=True, max_length=80)
            if not clean_name:
                clean_name = 'file'
            clean_name = f"{clean_name}{ext.lower()}"
            clean_url = f"/assets/{clean_name}"
            # Copy the file to output/assets/
            dest = os.path.join(OUTPUT_DIR, 'assets', clean_name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.exists(dest):
                shutil.copy2(abs_path, dest)
            # Add to asset_map for future lookups
            asset_map[rel_to_mapa] = clean_url
            return clean_url

    return None


def _extract_notion_id_from_url(url):
    """Extract 32-char hex Notion ID from a notion.so/notion.site URL."""
    # Pattern: ...page-name-<32hex> or ...<32hex>
    m = re.search(r'([a-f0-9]{32})', url.replace('-', ''))
    if m:
        return m.group(1)

    # Try with dashes: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    m = re.search(
        r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
        url
    )
    if m:
        return m.group(1).replace('-', '')

    return None
