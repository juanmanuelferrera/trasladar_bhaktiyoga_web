import os, re
from bs4 import BeautifulSoup
from urllib.parse import unquote

OUTPUT_DIR = '/Users/jaganat/.emacs.d/git_projects/trasladar_bhaktiyoga_web/output'

broken_links = []
broken_images = []

for root, dirs, files in os.walk(OUTPUT_DIR):
    for f in files:
        if not f.endswith('.html'):
            continue
        filepath = os.path.join(root, f)
        rel_page = os.path.relpath(filepath, OUTPUT_DIR)

        with open(filepath, 'r') as fh:
            soup = BeautifulSoup(fh.read(), 'html.parser')

        # Check href links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('#') or href.startswith('http') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            if href.startswith('about:'):
                broken_links.append((rel_page, href, 'about: link'))
                continue

            decoded = unquote(href.split('#')[0])
            if decoded.endswith('/'):
                target = os.path.join(OUTPUT_DIR, decoded.strip('/'), 'index.html')
            else:
                target = os.path.join(OUTPUT_DIR, decoded.strip('/'))
            target = os.path.normpath(target)

            if not os.path.exists(target):
                broken_links.append((rel_page, href, target))

        # Check img src
        for img in soup.find_all('img', src=True):
            src = img['src']
            if src.startswith('http') or src.startswith('data:'):
                continue
            decoded = unquote(src)
            target = os.path.normpath(os.path.join(OUTPUT_DIR, decoded.strip('/')))
            if not os.path.exists(target):
                broken_images.append((rel_page, src, target))

# Group by target
from collections import defaultdict
by_target = defaultdict(list)
for page, href, target in broken_links:
    by_target[href].append(page)

print(f"Total broken links: {len(broken_links)}")
print(f"Unique broken targets: {len(by_target)}")
print(f"Broken images: {len(broken_images)}")
print()

for href, pages in sorted(by_target.items(), key=lambda x: -len(x[1])):
    print(f"  {href}")
    print(f"    -> {len(pages)} pages: {pages[0]}" + (f" (+{len(pages)-1} more)" if len(pages) > 1 else ""))
print()

for page, src, target in broken_images:
    print(f"  BROKEN IMAGE: {page} -> {src}")
