"""Copy and organize media assets from Notion export."""
import os
import shutil
from slugify import slugify

from config import MAPA_DIR, EXISTING_ASSETS_DIR, OUTPUT_DIR


MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
    '.pdf', '.mp4', '.mp3', '.m4a', '.ogg', '.wav',
}


def copy_all_assets(asset_map):
    """
    Copy all media assets to output/assets/ using the asset_map.

    Args:
        asset_map: {relative_path_from_mapa: /assets/clean-name.ext}
    """
    output_assets = os.path.join(OUTPUT_DIR, 'assets')
    os.makedirs(output_assets, exist_ok=True)

    copied = 0
    errors = 0

    for rel_path, clean_url in asset_map.items():
        src = os.path.join(MAPA_DIR, rel_path)
        # clean_url is like /assets/filename.jpg
        dest_name = os.path.basename(clean_url)
        dest = os.path.join(output_assets, dest_name)

        if os.path.exists(src):
            try:
                shutil.copy2(src, dest)
                copied += 1
            except Exception as e:
                print(f"  ERROR copying {rel_path}: {e}")
                errors += 1
        else:
            # Try URL-decoded path
            import urllib.parse
            decoded_src = os.path.join(MAPA_DIR, urllib.parse.unquote(rel_path))
            if os.path.exists(decoded_src):
                try:
                    shutil.copy2(decoded_src, dest)
                    copied += 1
                except Exception as e:
                    print(f"  ERROR copying {rel_path}: {e}")
                    errors += 1
            else:
                errors += 1

    print(f"  Assets copied: {copied}, errors: {errors}")
    return copied, errors


def copy_existing_assets():
    """Copy the existing bhaktiyoga.es images to output."""
    output_assets = os.path.join(OUTPUT_DIR, 'assets')
    os.makedirs(output_assets, exist_ok=True)

    if not os.path.exists(EXISTING_ASSETS_DIR):
        return

    for f in os.listdir(EXISTING_ASSETS_DIR):
        src = os.path.join(EXISTING_ASSETS_DIR, f)
        dest = os.path.join(output_assets, f)
        if os.path.isfile(src):
            shutil.copy2(src, dest)
            print(f"  Copied existing asset: {f}")


def copy_static_files():
    """Copy static CSS/JS files to output."""
    from config import STATIC_DIR

    for subdir in ['css', 'js']:
        src_dir = os.path.join(STATIC_DIR, subdir)
        dest_dir = os.path.join(OUTPUT_DIR, subdir)
        if os.path.exists(src_dir):
            os.makedirs(dest_dir, exist_ok=True)
            for f in os.listdir(src_dir):
                src = os.path.join(src_dir, f)
                dest = os.path.join(dest_dir, f)
                if os.path.isfile(src):
                    shutil.copy2(src, dest)

    # Copy fonts if they exist
    fonts_dir = os.path.join(STATIC_DIR, 'fonts')
    if os.path.exists(fonts_dir):
        dest_fonts = os.path.join(OUTPUT_DIR, 'fonts')
        if os.path.exists(dest_fonts):
            shutil.rmtree(dest_fonts)
        shutil.copytree(fonts_dir, dest_fonts)

    # Copy root-level static files (favicon.svg, etc.) to output root
    for f in os.listdir(STATIC_DIR):
        src = os.path.join(STATIC_DIR, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(OUTPUT_DIR, f))


def build_asset_map():
    """
    Build mapping of original relative media paths to clean output paths.
    Returns {relative_path_from_mapa: /assets/clean-name.ext}
    """
    asset_map = {}
    seen_names = set()

    for root, dirs, files in os.walk(MAPA_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in MEDIA_EXTENSIONS:
                continue

            abs_path = os.path.join(root, f)
            rel_path = os.path.relpath(abs_path, MAPA_DIR)

            # Clean filename
            name_no_ext = os.path.splitext(f)[0]
            clean_name = slugify(name_no_ext, lowercase=True, max_length=80)
            if not clean_name:
                clean_name = "file"
            clean_name = f"{clean_name}{ext}"

            # Handle duplicates by prepending parent directory
            if clean_name in seen_names:
                parent = os.path.basename(root)
                parent_slug = slugify(parent, lowercase=True, max_length=30)
                clean_name = f"{parent_slug}-{clean_name}"

            # Still duplicate? Add counter
            base_clean = clean_name
            counter = 2
            while clean_name in seen_names:
                name_part = os.path.splitext(base_clean)[0]
                clean_name = f"{name_part}-{counter}{ext}"
                counter += 1

            seen_names.add(clean_name)
            asset_map[rel_path] = f"/assets/{clean_name}"

    return asset_map
