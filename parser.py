"""Parse Notion HTML exports and extract clean content."""
import os
import re
from bs4 import BeautifulSoup, NavigableString

# Map file extensions to icons and Spanish labels
_FILE_TYPE_MAP = {
    '.pdf':  ('pdf',   'PDF'),
    '.mp3':  ('audio', 'MP3'),
    '.mp4':  ('video', 'Video'),
    '.m4a':  ('audio', 'Audio'),
    '.ogg':  ('audio', 'OGG'),
    '.wav':  ('audio', 'WAV'),
    '.webm': ('video', 'Video'),
    '.zip':  ('file',  'ZIP'),
    '.epub': ('file',  'EPUB'),
    '.doc':  ('file',  'DOC'),
    '.docx': ('file',  'DOCX'),
}


def parse_notion_html(html_content):
    """
    Parse a Notion HTML export and return structured page data.

    Returns dict with:
        title: str
        content: str (cleaned inner HTML)
        cover_image: str or None
        is_hub: bool
        notion_id: str
        cards: list of {title, url, icon} for hub pages
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract title
    title_tag = soup.find('h1', class_='page-title')
    title = title_tag.get_text(strip=True) if title_tag else ''

    # Extract article ID (Notion UUID)
    article = soup.find('article')
    notion_id = ''
    if article and article.get('id'):
        notion_id = article['id'].replace('-', '')

    # Check for cover image
    cover_img = soup.find('img', class_='page-cover-image')
    cover_image = cover_img['src'] if cover_img else None

    # Get page body
    page_body = soup.find('div', class_='page-body')
    if not page_body:
        return {
            'title': title,
            'content': '',
            'cover_image': cover_image,
            'is_hub': False,
            'notion_id': notion_id,
            'cards': [],
        }

    # Strip Notion navigation header (INICIO / CONTENIDO / LIBRERIA)
    _strip_notion_nav(page_body)

    # Strip Notion footer (donation section + copyright)
    _strip_notion_footer(page_body)

    # Strip properties table
    _strip_properties_table(page_body)

    # Unwrap display:contents divs
    _unwrap_display_contents(page_body)

    # Strip empty paragraphs
    _strip_empty_paragraphs(page_body)

    # Strip personal address/phone, keep only email
    _strip_personal_contact(page_body)

    # Strip Notion icon images (database table header decoration)
    _strip_notion_icons(page_body)

    # Replace CDN references with local paths
    _localize_cdn_refs(page_body)

    # Beautify ugly S3/Notion download links
    _beautify_download_links(page_body)

    # Detect hub pages and extract cards
    is_hub = False
    cards = []
    collection_table = page_body.find('table', class_='collection-content')
    if collection_table:
        # Only treat as hub if the page is primarily a collection,
        # not an article that happens to embed a small database view.
        non_table_text = ''.join(
            el.get_text(strip=True) for el in page_body.children
            if el != collection_table and hasattr(el, 'get_text')
        )
        if len(non_table_text) < 1500:
            is_hub = True
            cards = _extract_cards_from_table(collection_table)

    # Also detect hub-like pages that are just lists of links
    if not is_hub:
        links = page_body.find_all('a')
        link_to_pages = page_body.find_all('figure', class_='link-to-page')
        if len(link_to_pages) > 3:
            is_hub = True
            cards = _extract_cards_from_links(link_to_pages)

    # Get cleaned inner HTML
    content = page_body.decode_contents()

    # Clean up excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    return {
        'title': title,
        'content': content,
        'cover_image': cover_image,
        'is_hub': is_hub,
        'notion_id': notion_id,
        'cards': cards,
    }


def _strip_notion_nav(soup):
    """Remove the INICIO / CONTENIDO / LIBRERIA navigation header."""
    # It's typically the first h3 containing links to bhakti.pages.dev or CONTENIDO
    for h3 in soup.find_all('h3', limit=3):
        text = h3.get_text()
        if any(kw in text for kw in ['INICIO', 'CONTENIDO', 'LIBRERÍA', 'LIBRERIA']):
            h3.decompose()
            break


def _strip_notion_footer(soup):
    """Remove donation section and copyright from bottom."""
    # Look for "¿Te gusta lo que hacemos?" heading
    for tag in soup.find_all(['h3', 'h2', 'p']):
        text = tag.get_text()
        if '¿Te gusta lo que hacemos?' in text or 'Te gusta lo que hacemos' in text:
            # Remove this tag and everything after it
            next_siblings = list(tag.find_next_siblings())
            tag.decompose()
            for sib in next_siblings:
                if hasattr(sib, 'decompose'):
                    sib.decompose()
            break

    # Also remove copyright line
    for p in soup.find_all('p'):
        text = p.get_text()
        if '©' in text and 'Centros Bhakti-yoga' in text:
            p.decompose()
        elif '©️' in text and 'Bhakti' in text:
            p.decompose()


def _strip_properties_table(soup):
    """Remove Notion properties metadata table."""
    for table in soup.find_all('table', class_='properties'):
        table.decompose()


def _unwrap_display_contents(soup):
    """Unwrap div wrappers that have display:contents style."""
    for div in soup.find_all('div', style=re.compile(r'display:\s*contents')):
        div.unwrap()


def _strip_empty_paragraphs(soup):
    """Remove paragraphs that are empty or contain only whitespace."""
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if not text or text == '\xa0':
            # Check if it has no meaningful child elements (images, etc.)
            has_meaningful = any(
                child.name in ('img', 'a', 'iframe', 'video', 'audio')
                for child in p.find_all()
            )
            if not has_meaningful:
                p.decompose()


def _extract_cards_from_table(table):
    """Extract card data from a Notion collection-content table."""
    cards = []
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if not cells:
            continue

        # First cell usually has the title/link
        link = cells[0].find('a')
        if not link:
            continue

        title = link.get_text(strip=True)
        url = link.get('href', '')

        # Check for icon
        icon = None
        icon_tag = cells[0].find('span', class_='icon')
        if icon_tag:
            icon_img = icon_tag.find('img')
            if icon_img:
                icon = icon_img.get('src', '')

        # Check for description in other cells
        description = ''
        if len(cells) > 1:
            description = cells[1].get_text(strip=True)

        if title:
            cards.append({
                'title': title,
                'url': url,
                'icon': icon,
                'description': description,
                'image': None,
            })

    return cards


def _extract_cards_from_links(link_figures):
    """Extract cards from link-to-page figures."""
    cards = []
    for fig in link_figures:
        link = fig.find('a')
        if not link:
            continue

        title = link.get_text(strip=True)
        url = link.get('href', '')

        if title:
            cards.append({
                'title': title,
                'url': url,
                'icon': None,
                'description': '',
                'image': None,
            })

    return cards


def _strip_personal_contact(soup):
    """Remove physical address and phone number paragraphs, keep only email."""
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text.startswith('🏡') or text.startswith('☎️'):
            p.decompose()


def _strip_notion_icons(soup):
    """Remove Notion icon images (tiny decorative icons in database table headers)."""
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if 'notion.so/icons/' in src:
            parent = img.parent
            img.decompose()
            # Remove the empty span wrapper too
            if parent and parent.name == 'span' and not parent.get_text(strip=True):
                parent.decompose()


def _localize_cdn_refs(soup):
    """Remove CDN script/link tags (Prism.js etc.) — not needed."""
    for script in soup.find_all('script', src=True):
        if 'cdnjs.cloudflare.com' in script['src']:
            script.decompose()
    for link in soup.find_all('link', href=True):
        if 'cdnjs.cloudflare.com' in link['href']:
            link.decompose()


def _beautify_download_links(soup):
    """
    Replace ugly S3/Notion URLs in link text with clean download cards.

    Targets patterns like:
        <figure><div class="source"><a href="/assets/file.pdf">
            https://s3-us-west-2.amazonaws.com/.../file.pdf
        </a></div></figure>

    Also catches any <a> whose visible text contains notion-static.com
    """
    ugly_patterns = [
        'secure.notion-static.com',
        's3-us-west-2.amazonaws.com',
        'notion-static.com',
        'prod-files-secure',
    ]

    for a_tag in soup.find_all('a'):
        link_text = a_tag.get_text(strip=True)

        # Check if the visible text contains an ugly URL
        if not any(pat in link_text for pat in ugly_patterns):
            continue

        href = a_tag.get('href', '')

        # Derive clean label from the href (already rewritten to /assets/...)
        if href:
            filename = os.path.basename(href)
            name, ext = os.path.splitext(filename)
        else:
            # Fallback: try to get filename from the ugly URL text
            try:
                filename = link_text.rstrip('/').split('/')[-1]
                name, ext = os.path.splitext(filename)
            except Exception:
                name, ext = 'archivo', ''

        ext_lower = ext.lower()
        file_cat, file_label = _FILE_TYPE_MAP.get(ext_lower, ('file', ext_lower.lstrip('.').upper() or 'Archivo'))

        # Clean up the name: replace hyphens/underscores with spaces, title case
        display_name = name.replace('-', ' ').replace('_', ' ').strip()
        display_name = display_name.title()

        # Build the new link content as a download card
        a_tag.clear()
        a_tag['class'] = a_tag.get('class', []) + ['download-card']
        a_tag['download'] = ''

        # Create inner structure by parsing HTML fragment
        card_html = (
            f'<span class="download-card__icon download-card__icon--{file_cat}"></span>'
            f'<span class="download-card__info">'
            f'<span class="download-card__name">{display_name}</span>'
            f'<span class="download-card__type">Descargar {file_label}</span>'
            f'</span>'
        )
        card_fragment = BeautifulSoup(card_html, 'html.parser')
        for child in list(card_fragment.children):
            a_tag.append(child)

        # If the <a> is inside a <div class="source">, restyle the parent figure
        source_div = a_tag.find_parent('div', class_='source')
        if source_div:
            source_div['class'] = ['download-card-wrapper']
            parent_figure = source_div.find_parent('figure')
            if parent_figure:
                parent_figure['class'] = parent_figure.get('class', []) + ['download-figure']
