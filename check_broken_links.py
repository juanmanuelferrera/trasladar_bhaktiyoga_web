#!/usr/bin/env python3
"""
Broken Internal Link Scanner for bhaktiyoga.es static site.

Scans all HTML files in the output/ directory for broken internal links
and broken image references.
"""

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin, unquote
from pathlib import Path
from collections import defaultdict


OUTPUT_DIR = Path("/Users/jaganat/.emacs.d/git_projects/trasladar_bhaktiyoga_web/output")


class LinkExtractor(HTMLParser):
    """Extract href and src attributes from HTML files."""

    def __init__(self):
        super().__init__()
        self.links = []  # (tag, attr_name, url, line)

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Extract href from <a>, <link>, <area>
        if tag in ("a", "link", "area") and "href" in attrs_dict:
            self.links.append((tag, "href", attrs_dict["href"], self.getpos()[0]))
        # Extract src from <img>, <script>, <source>, <video>, <audio>, <iframe>
        if tag in ("img", "script", "source", "video", "audio", "iframe") and "src" in attrs_dict:
            self.links.append((tag, "src", attrs_dict["src"], self.getpos()[0]))
        # Extract srcset from <img>, <source>
        if tag in ("img", "source") and "srcset" in attrs_dict:
            srcset = attrs_dict["srcset"]
            for entry in srcset.split(","):
                entry = entry.strip()
                if entry:
                    url = entry.split()[0]
                    self.links.append((tag, "srcset", url, self.getpos()[0]))
        # Extract poster from <video>
        if tag == "video" and "poster" in attrs_dict:
            self.links.append((tag, "poster", attrs_dict["poster"], self.getpos()[0]))


def is_internal_link(url):
    """Check if a URL is an internal link (not external, not anchor-only, not special)."""
    if not url or url.strip() == "":
        return False
    url = url.strip()
    # Skip anchor-only links
    if url.startswith("#"):
        return False
    # Skip mailto, tel, javascript, data URIs
    if re.match(r'^(mailto:|tel:|javascript:|data:)', url, re.IGNORECASE):
        return False
    # Skip external links
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https", "ftp"):
        return False
    # This is an internal link (relative or absolute path)
    return True


def resolve_link(source_html_path, href, output_dir):
    """
    Resolve an internal link to a filesystem path.
    Returns (resolved_path, exists).
    """
    href = unquote(href)
    # Strip fragment
    href_no_frag = href.split("#")[0]
    if not href_no_frag:
        # It's just an anchor on the same page - skip
        return None, True

    if href_no_frag.startswith("/"):
        # Absolute path from site root
        resolved = output_dir / href_no_frag.lstrip("/")
    else:
        # Relative path from the source file's directory
        source_dir = source_html_path.parent
        resolved = (source_dir / href_no_frag).resolve()

    # Check existence:
    # 1. Exact file exists
    if resolved.is_file():
        return resolved, True
    # 2. It's a directory - check for index.html inside
    if resolved.is_dir():
        index = resolved / "index.html"
        if index.is_file():
            return index, True
        else:
            return resolved, False
    # 3. Try appending index.html if path looks like a directory ref (ends with /)
    if str(href_no_frag).endswith("/"):
        pass  # Already handled by is_dir check above
    # 4. Try adding .html extension
    resolved_html = resolved.with_suffix(".html")
    if resolved_html.is_file():
        return resolved_html, True
    # 5. Path doesn't exist at all
    return resolved, False


def scan_html_file(html_path, output_dir):
    """Scan a single HTML file for broken internal links."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return [], [], 0

    parser = LinkExtractor()
    try:
        parser.feed(content)
    except Exception as e:
        return [], [], 0

    broken_links = []
    broken_images = []
    total_checked = 0

    for tag, attr, url, line in parser.links:
        if not is_internal_link(url):
            continue

        total_checked += 1
        resolved, exists = resolve_link(html_path, url, output_dir)

        if resolved is None:
            # Anchor-only after stripping fragment
            continue

        if not exists:
            try:
                expected_rel = str(resolved.relative_to(output_dir))
            except ValueError:
                expected_rel = str(resolved)

            entry = {
                "source": str(html_path.relative_to(output_dir)),
                "tag": tag,
                "attr": attr,
                "href": url,
                "expected": expected_rel,
                "line": line,
            }
            if attr in ("src", "srcset", "poster"):
                broken_images.append(entry)
            else:
                broken_links.append(entry)

    return broken_links, broken_images, total_checked


def main():
    output_dir = OUTPUT_DIR.resolve()
    if not output_dir.is_dir():
        print(f"ERROR: Output directory not found: {output_dir}")
        sys.exit(1)

    # Collect all HTML files
    html_files = sorted(output_dir.rglob("*.html"))
    print(f"Found {len(html_files)} HTML files in {output_dir}\n")

    all_broken_links = []
    all_broken_images = []
    total_internal_links = 0

    for html_path in html_files:
        broken_links, broken_images, checked = scan_html_file(html_path, output_dir)
        total_internal_links += checked
        all_broken_links.extend(broken_links)
        all_broken_images.extend(broken_images)

    # -- Report --
    print("=" * 80)
    print("  BROKEN INTERNAL LINK REPORT FOR bhaktiyoga.es")
    print("=" * 80)
    print(f"\n  HTML files scanned:           {len(html_files)}")
    print(f"  Total internal links checked: {total_internal_links}")
    print(f"  Broken links found:           {len(all_broken_links)}")
    print(f"  Broken images found:          {len(all_broken_images)}")
    print()

    if all_broken_links:
        print("-" * 80)
        print("  BROKEN LINKS (grouped by source page)")
        print("-" * 80)

        grouped = defaultdict(list)
        for entry in all_broken_links:
            grouped[entry["source"]].append(entry)

        for source in sorted(grouped.keys()):
            print(f"\n  [{source}]")
            for e in grouped[source]:
                print(f"    Line {e['line']:>4}: <{e['tag']} {e['attr']}=\"{e['href']}\">")
                print(f"            Expected file: {e['expected']}")
        print()

    if all_broken_images:
        print("-" * 80)
        print("  BROKEN IMAGE / MEDIA REFERENCES (grouped by source page)")
        print("-" * 80)

        grouped = defaultdict(list)
        for entry in all_broken_images:
            grouped[entry["source"]].append(entry)

        for source in sorted(grouped.keys()):
            print(f"\n  [{source}]")
            for e in grouped[source]:
                print(f"    Line {e['line']:>4}: <{e['tag']} {e['attr']}=\"{e['href']}\">")
                print(f"            Expected file: {e['expected']}")
        print()

    if not all_broken_links and not all_broken_images:
        print("  No broken internal links or images found!")
        print()

    # -- Summary of unique broken targets --
    if all_broken_links or all_broken_images:
        all_broken = all_broken_links + all_broken_images
        unique_targets = sorted(set(e["href"] for e in all_broken))
        print("-" * 80)
        print(f"  UNIQUE BROKEN TARGETS ({len(unique_targets)} total)")
        print("-" * 80)
        for target in unique_targets:
            count = sum(1 for e in all_broken if e["href"] == target)
            print(f"    {target}  ({count} reference{'s' if count > 1 else ''})")
        print()

    print("=" * 80)
    print("  SCAN COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
