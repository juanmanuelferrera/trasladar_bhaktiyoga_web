"""Build a mapping of Notion hash IDs to clean URL slugs."""
import os
import re
import urllib.parse
from slugify import slugify
from config import MAPA_DIR, SLUG_OVERRIDES

# Regex to extract title and Notion ID from filenames
# e.g., "Estatutos 55e021b5b0194c9ebaba695a74433538.html"
NOTION_FILENAME_RE = re.compile(r'^(.+?)\s+([a-f0-9]{32})\.html$')
# Short hash pattern (some files use truncated IDs)
NOTION_SHORT_RE = re.compile(r'^(.+?)\s+([a-f0-9]{4}-[a-f0-9]{4})\.html$')


def extract_notion_id(filename):
    """Extract the Notion hash ID from a filename."""
    m = NOTION_FILENAME_RE.match(filename)
    if m:
        return m.group(1).strip(), m.group(2)
    m = NOTION_SHORT_RE.match(filename)
    if m:
        return m.group(1).strip(), m.group(2)
    return None, None


def build_slug_map():
    """
    Walk the Mapa de la web directory and build mappings:
    - slug_map: {notion_id: clean_url_path}
    - file_map: {notion_id: absolute_file_path}
    - title_map: {notion_id: page_title}
    """
    slug_map = {}
    file_map = {}
    title_map = {}
    parent_map = {}  # notion_id -> parent directory context

    for root, dirs, files in os.walk(MAPA_DIR):
        for f in files:
            if not f.endswith('.html'):
                continue

            title, notion_id = extract_notion_id(f)
            if not notion_id:
                continue

            abs_path = os.path.join(root, f)
            rel_path = os.path.relpath(root, MAPA_DIR)

            file_map[notion_id] = abs_path
            title_map[notion_id] = title

            # Check for manual override
            if notion_id in SLUG_OVERRIDES:
                slug_map[notion_id] = SLUG_OVERRIDES[notion_id]
                continue

            # Build slug from directory context + title
            slug = make_slug(title, rel_path)
            slug_map[notion_id] = slug

    return slug_map, file_map, title_map


def make_slug(title, rel_dir_path):
    """
    Create a clean URL slug from title and directory context.
    Flattens deep Notion nesting into 2-3 level URLs.
    """
    # Decode any URL encoding in the title
    title = urllib.parse.unquote(title)

    # Generate base slug from title
    base_slug = slugify(title, lowercase=True, max_length=60)
    if not base_slug:
        base_slug = "page"

    # Determine section from directory path
    if rel_dir_path == '.':
        # Top-level page
        return f"/{base_slug}/"

    parts = rel_dir_path.split(os.sep)
    # Decode directory names
    parts = [urllib.parse.unquote(p) for p in parts]

    # Map top-level directories to sections
    section_map = {
        "Blog": "blog",
        "Contenido": "contenido",
        "Librería": "libreria",
        "Eventos": "eventos",
        "Talleres": "talleres",
        "Conferencias": "conferencias",
        "Videos": "videos",
        "Catálogo": "catalogo",
        "La Casa de Krsna": "la-casa-de-krsna",
        "Curso de Bhakti yoga": "curso-de-bhakti-yoga",
        "Revista": "revista",
        "Glosario": "glosario",
        "The Book": "prabhupada-now/the-book",
        "Passages": "prabhupada-now/passages",
        "About": "prabhupada-now/about",
        "Asistencia": "asistencia",
    }

    # Find the first meaningful section from directory parts
    section = None
    for p in parts:
        # Strip Notion ID from directory name
        clean = NOTION_FILENAME_RE.sub(r'\1', p + '.html').replace('.html', '').strip()
        if not clean:
            clean = p
        if clean in section_map:
            section = section_map[clean]
            break
        # Try slugified version
        for key, val in section_map.items():
            if slugify(key) == slugify(clean):
                section = val
                break
        if section:
            break

    if not section:
        # Try to build from first directory part
        first_dir = parts[0]
        # Strip any Notion ID from directory name
        m = re.match(r'^(.+?)\s+[a-f0-9]{32}$', first_dir)
        if m:
            first_dir = m.group(1)
        section = slugify(first_dir, lowercase=True, max_length=40)

    # Skip intermediate "Untitled", "Temas", "Categorías", "Recetas" (duplicate) dirs
    skip_dirs = {"untitled", "temas", "categorias", "categorías"}

    # Build sub-path from remaining meaningful directories
    sub_parts = []
    found_section = False
    for p in parts:
        clean = re.sub(r'\s+[a-f0-9]{32}$', '', p).strip()
        clean = urllib.parse.unquote(clean)
        clean_slug = slugify(clean, lowercase=True)
        if not found_section:
            # Skip until we pass the section directory
            if clean_slug == section.split('/')[0] or clean in section_map:
                found_section = True
            continue
        if clean_slug in skip_dirs:
            continue
        if clean_slug and clean_slug != base_slug:
            sub_parts.append(clean_slug)

    # Assemble final URL
    if sub_parts:
        return f"/{section}/{'/'.join(sub_parts)}/{base_slug}/"
    else:
        return f"/{section}/{base_slug}/"


def build_asset_path_map():
    """
    Build a mapping of original relative media paths to clean output paths.
    Returns {relative_path_from_mapa: /assets/clean-name.ext}
    """
    asset_map = {}
    seen_names = set()

    media_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.pdf', '.mp4', '.mp3'}

    for root, dirs, files in os.walk(MAPA_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in media_exts:
                continue

            abs_path = os.path.join(root, f)
            rel_path = os.path.relpath(abs_path, MAPA_DIR)

            # Clean filename
            clean_name = slugify(os.path.splitext(f)[0], lowercase=True, max_length=80)
            if not clean_name:
                clean_name = "file"
            clean_name = f"{clean_name}{ext}"

            # Handle duplicates
            if clean_name in seen_names:
                parent = os.path.basename(root)
                parent_slug = slugify(parent, lowercase=True, max_length=30)
                clean_name = f"{parent_slug}-{clean_name}"

            seen_names.add(clean_name)
            asset_map[rel_path] = f"/assets/{clean_name}"

    return asset_map


if __name__ == "__main__":
    slug_map, file_map, title_map = build_slug_map()
    print(f"Found {len(slug_map)} pages:")
    for nid, slug in sorted(slug_map.items(), key=lambda x: x[1]):
        print(f"  {slug:60s} <- {title_map.get(nid, '?')}")

    asset_map = build_asset_path_map()
    print(f"\nFound {len(asset_map)} assets")
