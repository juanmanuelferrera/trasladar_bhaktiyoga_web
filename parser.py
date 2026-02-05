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

    # Transform Anchor/podcast links into nice cards
    _beautify_podcast_links(page_body)

    # Embed YouTube videos
    _embed_youtube_videos(page_body)

    # Beautify ugly S3/Notion download links
    _beautify_download_links(page_body)

    # Beautify raw Amazon/Leanpub URLs in table cells
    _beautify_table_urls(page_body)

    # Beautify raw external URLs (Stripe, archive.org, Indify, etc.)
    _beautify_raw_urls(page_body)

    # Strip Bizum donation images
    _strip_bizum_images(page_body)

    # Strip empty wrapper divs
    _strip_empty_divs(page_body)

    # Fix about:blank footnote links (Notion exports them with about:blank prefix)
    _fix_about_blank_links(page_body)

    # Strip data: URI links (base64 images used as href instead of src)
    _strip_data_uri_links(page_body)

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

    # If hub page, strip the collection table from visible content
    # (cards are already extracted and will be rendered as a card grid)
    if is_hub and collection_table:
        # Remove the collection-content wrapper div (table + heading)
        for coll_div in page_body.find_all('div', class_='collection-content'):
            coll_div.decompose()
        # Also remove standalone collection tables
        for table in page_body.find_all('table', class_='collection-content'):
            table.decompose()

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
    """Remove paragraphs that are empty, whitespace-only, or placeholder text."""
    placeholder_texts = {'', '\xa0', 'website'}
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text.lower() in placeholder_texts:
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

        # Check for description in other cells (skip timestamp/date columns)
        description = ''
        if len(cells) > 1:
            cell_text = cells[1].get_text(strip=True)
            # Skip Notion timestamp values like "@September 6, 2021 6:36 PM"
            if cell_text and not cell_text.startswith('@'):
                description = cell_text

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


# Clean titles for podcast episodes (URL slugs lose accents)
_PODCAST_TITLES = {
    'Julia-Samadhi': 'Julia Samadhi',
    'Nutrirse--algo-ms-que-comer': 'Nutrirse, algo más que comer',
    'Teologa-prctica-con-Luis-Roger': 'Teología práctica con Luis Roger',
    'Ciencia--evolucin-y-el-origen-de-la-vida': 'Ciencia, evolución y el origen de la vida',
    'Crecer-en-Libertad-con-Ana-Dragow': 'Crecer en libertad con Ana Dragow',
    'Un-rato-con-Gabriele': 'Un rato con Gabriele',
    'In-La-Alpujarra--getting-high-English': 'In La Alpujarra, Getting High (English)',
    'Benedict--the-Happy-Host-English': 'Benedict, the Happy Host (English)',
    'Sat-Prema--el-artista-mstico': 'Sat Prema, el artista místico',
    'Cantando-Hare-Krishna-en-la-radio-2009': 'Cantando Hare Krishna en la radio (2009)',
    'Conversacin-con-la-sobrina-de-Sucih-Srava-Dasa': 'Conversación con la sobrina de Sucih Srava Dasa',
    'Japa-soft-chanting-meditation': 'Japa: Soft Chanting Meditation',
    'Temple-management': 'Temple Management',
    'The-duties-of-a-temple-president': 'The Duties of a Temple President',
    'Book-distribution': 'Book Distribution',
    'Spiritual-Program': 'Spiritual Program',
    'Krishnas-test': "Krishna's Test",
    'Book-distribution-and-temple': 'Book Distribution and Temple',
    'Cat-Alarm': 'Cat Alarm',
}


def _extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats."""
    # youtube.com/watch?v=ID
    m = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # youtu.be/ID
    m = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    return None


def _embed_youtube_videos(soup):
    """Convert raw YouTube links into responsive embedded iframes."""
    # Collect all targets first to avoid tree modification during iteration
    targets = []
    for figure in list(soup.find_all('figure')):
        source_div = figure.find('div', class_='source')
        if not source_div:
            continue
        a_tag = source_div.find('a', href=True)
        if not a_tag:
            continue
        href = a_tag['href']
        video_id = _extract_youtube_id(href)
        if video_id:
            targets.append((figure, video_id))

    for figure, video_id in targets:
        embed_html = (
            f'<div class="video-embed">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{video_id}" '
            f'frameborder="0" allowfullscreen loading="lazy" '
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">'
            f'</iframe>'
            f'</div>'
        )
        new_tag = BeautifulSoup(embed_html, 'html.parser')
        figure.replace_with(new_tag)


def _beautify_podcast_links(soup):
    """Transform raw Anchor.fm/Spotify links into a podcast episode grid."""
    anchor_figures = []
    for figure in soup.find_all('figure'):
        a_tag = figure.find('a', href=True)
        if a_tag and 'anchor.fm' in a_tag['href']:
            anchor_figures.append(figure)

    if not anchor_figures:
        return

    # Extract episode info from URLs
    episodes = []
    for fig in anchor_figures:
        a_tag = fig.find('a', href=True)
        url = a_tag['href']
        # Extract episode slug from URL
        slug_part = url.rstrip('/').split('/episodes/')[-1] if '/episodes/' in url else ''
        # Remove the trailing episode ID (e.g. -e182u28)
        title_slug = re.sub(r'-e[a-z0-9]+$', '', slug_part)
        # Look up clean title or generate from slug
        title = _PODCAST_TITLES.get(title_slug, title_slug.replace('-', ' ').title())
        if title:
            episodes.append({'title': title, 'url': url})

    if not episodes:
        return

    # Build the podcast grid HTML
    podcast_icon = (
        '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M12 1C5.93 1 1 5.93 1 12s4.93 11 11 11 11-4.93 11-11S18.07 1 12 1zm3.29 '
        '16.71L12 14.42l-3.29 3.29c-.39.39-1.03.39-1.42 0s-.39-1.03 0-1.42L10.59 13 7.29 '
        '9.71c-.39-.39-.39-1.03 0-1.42.39-.39 1.03-.39 1.42 0L12 11.59l3.29-3.29c.39-.39 '
        '1.03-.39 1.42 0s.39 1.03 0 1.42L13.41 13l3.29 3.29c.39.39.39 1.03 0 1.42-.39.39'
        '-1.02.39-1.41 0z" fill="currentColor" opacity="0.5"/>'
        '<circle cx="12" cy="12" r="3" fill="currentColor"/>'
        '<path d="M12 1v4m0 14v4M1 12h4m14 0h4" stroke="currentColor" stroke-width="1" '
        'opacity="0.3"/></svg>'
    )

    # Build headphone icon for podcast
    headphone_svg = (
        '<svg class="podcast-card__icon" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 3C7.03 3 3 7.03 3 12v7c0 1.1.9 2 2 2h1c1.1 0 2-.9 2-2v-3c0-1.1-.9-2'
        '-2-2H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-1c-1.1 0-2 .9-2 2v3c0 1.1.9 2 2 2h1c'
        '1.1 0 2-.9 2-2v-7c0-4.97-4.03-9-9-9z" fill="currentColor"/>'
        '</svg>'
    )

    grid_html = '<div class="podcast-grid">'
    for ep in episodes:
        grid_html += (
            f'<a href="{ep["url"]}" class="podcast-card" target="_blank" '
            f'rel="noopener noreferrer">'
            f'{headphone_svg}'
            f'<span class="podcast-card__title">{ep["title"]}</span>'
            f'<span class="podcast-card__listen">Escuchar &rarr;</span>'
            f'</a>'
        )
    grid_html += '</div>'

    # Replace all anchor figures with the grid
    new_tag = BeautifulSoup(grid_html, 'html.parser')
    anchor_figures[0].insert_before(new_tag)
    for fig in anchor_figures:
        fig.decompose()

    # Also remove empty column-lists and Bizum image that follow
    for col_list in soup.find_all('div', class_='column-list'):
        # Check if all columns are empty
        if not col_list.get_text(strip=True):
            col_list.decompose()

    # Remove Bizum donation image if present
    for fig in soup.find_all('figure', class_='image'):
        img = fig.find('img')
        if img and 'bizum' in img.get('src', '').lower():
            parent_div = fig.parent
            fig.decompose()
            if parent_div and parent_div.name == 'div' and not parent_div.get_text(strip=True):
                parent_div.decompose()


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


def _strip_bizum_images(soup):
    """Remove Bizum donation images that leak through footer stripping."""
    for fig in list(soup.find_all('figure', class_='image')):
        img = fig.find('img')
        if img and 'bizum' in img.get('src', '').lower():
            parent = fig.parent
            fig.decompose()
            # Remove empty wrapper div too
            if parent and parent.name == 'div' and not parent.get_text(strip=True):
                parent.decompose()


def _strip_empty_divs(soup):
    """Remove empty <div></div> wrappers that add dead whitespace."""
    for div in list(soup.find_all('div')):
        if not div.get_text(strip=True) and not div.find_all(['img', 'iframe', 'video', 'audio', 'svg', 'figure', 'table', 'a']):
            # Don't remove divs with meaningful classes
            classes = div.get('class', [])
            if not any(c for c in classes if c not in ('', 'indented')):
                div.decompose()


def _beautify_table_urls(soup):
    """Replace raw Amazon/Leanpub URLs in table cells with styled short links."""
    for a_tag in soup.find_all('a', class_='url-value'):
        href = a_tag.get('href', '')
        if 'amazon' in href:
            a_tag.string = 'Amazon'
            a_tag['class'] = ['table-buy-link']
        elif 'leanpub' in href:
            a_tag.string = 'Leanpub'
            a_tag['class'] = ['table-buy-link']
        a_tag['target'] = '_blank'
        a_tag['rel'] = 'noopener noreferrer'


# URL label map for beautifying raw external URLs
_RAW_URL_LABELS = {
    'buy.stripe.com': ('Comprar', 'stripe'),
    'indify.co': None,  # Remove entirely (widget placeholder)
    'archive.org': ('Escuchar en Archive.org', 'audio'),
    'audio.iskcondesiretree': ('Escuchar audio', 'audio'),
    'open.spotify.com': ('Escuchar en Spotify', 'audio'),
    'dropbox.com': ('Descargar documento', 'file'),
    'leanpub.com': ('Comprar e-book', 'book'),
    'prabhupadavani.org': ('Visitar Prabhupadavani.org', 'link'),
}


def _beautify_raw_urls(soup):
    """Transform raw external URLs in <div class='source'> into styled link cards."""
    for figure in list(soup.find_all('figure')):
        source_div = figure.find('div', class_='source')
        if not source_div:
            continue
        a_tag = source_div.find('a', href=True)
        if not a_tag:
            continue

        href = a_tag['href']
        link_text = a_tag.get_text(strip=True)

        # Skip already-processed download cards and YouTube embeds
        if 'download-card' in a_tag.get('class', []):
            continue
        if 'youtube' in href or 'youtu.be' in href:
            continue

        # Find matching domain
        matched_label = None
        matched_type = 'link'
        for domain, config in _RAW_URL_LABELS.items():
            if domain in href or domain in link_text:
                if config is None:
                    # Remove entirely (e.g. Indify widget placeholders)
                    figure.decompose()
                    matched_label = '__removed__'
                    break
                matched_label, matched_type = config
                break

        if matched_label == '__removed__':
            continue

        if not matched_label:
            # For unrecognized URLs, create a generic styled link
            if href.startswith('http'):
                matched_label = 'Visitar enlace'
                matched_type = 'link'
            else:
                continue

        # Build styled external link card
        icon_map = {
            'stripe': '💳',
            'audio': '🎵',
            'book': '📖',
            'file': '📄',
            'link': '🔗',
        }
        icon = icon_map.get(matched_type, '🔗')

        card_html = (
            f'<a href="{href}" class="external-link-card external-link-card--{matched_type}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'<span class="external-link-card__icon">{icon}</span>'
            f'<span class="external-link-card__label">{matched_label}</span>'
            f'</a>'
        )
        new_tag = BeautifulSoup(card_html, 'html.parser')
        figure.replace_with(new_tag)


def _fix_about_blank_links(soup):
    """Strip 'about:blank' prefix from footnote links.

    Notion sometimes exports footnotes as about:blank#fn-1 instead of #fn-1.
    """
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('about:blank#'):
            a['href'] = href.replace('about:blank', '')


def _strip_data_uri_links(soup):
    """Remove <a> tags whose href is a data: URI (e.g. base64-encoded images).

    These are malformed Notion exports where a base64 image was placed in an
    href instead of an img src.  We unwrap the link but keep its contents.
    """
    for a in list(soup.find_all('a', href=True)):
        if a['href'].startswith('data:'):
            a.unwrap()
