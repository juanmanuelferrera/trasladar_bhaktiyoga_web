"""Configuration for bhaktiyoga.es static site builder."""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTION_EXPORT_DIR = os.path.join(
    BASE_DIR, "notion_full", "Export-c6d3c031-f0ff-4631-b482-cca26e5f9b70"
)
MAPA_DIR = os.path.join(NOTION_EXPORT_DIR, "Mapa de la web")
EXISTING_ASSETS_DIR = os.path.join(BASE_DIR, "existing_assets")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Site info
SITE_NAME = "Centros de Bhakti yoga"
SITE_TAGLINE = "La ciencia de la relación con el Supremo"
SITE_CIF = "Entidad No Lucrativa | CIF G-76660679"
SITE_LANG = "es"
SITE_URL = "https://www.bhaktiyoga.es"
CONTACT_EMAIL = "info@bhaktiyoga.es"
CONTACT_TELEGRAM = "https://t.me/mishradas"

# Navigation structure
MAIN_NAV = [
    {"label": "Inicio", "url": "/", "children": []},
    {
        "label": "Enseñanzas",
        "url": "/contenido/",
        "children": [
            {"label": "Contenido", "url": "/contenido/"},
            {"label": "Blog", "url": "/blog/"},
            {"label": "Librería", "url": "/libreria/"},
            {"label": "Curso de Bhakti Yoga", "url": "/curso-de-bhakti-yoga/"},
            {"label": "Srila Prabhupada", "url": "/a-c-bhaktivedanta-swami-prabhupada/"},
        ],
    },
    # {
    #     "label": "Eventos",
    #     "url": "/eventos/",
    #     "children": [
    #         {"label": "Conferencias", "url": "/conferencias/"},
    #         {"label": "Talleres", "url": "/talleres/"},
    #         {"label": "Eventos", "url": "/eventos/"},
    #     ],
    # },
    {
        "label": "Comunidad",
        "url": "/estatutos/",
        "children": [
            {"label": "Glosario", "url": "/glosario/"},
            {"label": "Revista", "url": "/revista/"},
            {"label": "La Casa de Krsna", "url": "/la-casa-de-krsna/"},
            {"label": "Catálogo", "url": "/catalogo/"},
            {"label": "Estatutos", "url": "/estatutos/"},
        ],
    },
    {"label": "Contacto", "url": "/asistencia/", "children": []},
    {"label": "🇬🇧 EN", "url": "/en/", "children": []},
]

# Sections that are "hub" pages (use card grid layout)
HUB_SECTIONS = {
    "blog", "contenido", "libreria", "eventos", "talleres",
    "conferencias", "videos", "revista", "catalogo",
}

# Manual slug overrides for known pages
SLUG_OVERRIDES = {
    "55e021b5b0194c9ebaba695a74433538": "/estatutos/",
    "4de5e2fd65e8460e90aeb8f0a256ecfc": "/contenido/",
    "8f04e519bdb746158a24ba0010b813ef": "/libreria/",
    "d8a09ede1598464693ac1750b9ba2cce": "/blog/",
    "361c82e1b1b7464ab15e16c230a2db53": "/",
    "2dbe846ade1b428ca98b39027e796313": "/centros/",
}

# Featured portrait images (slug → image path) — floated right beside text
FEATURED_IMAGES = {
    "/a-c-bhaktivedanta-swami-prabhupada/": {
        "src": "/assets/prabhupada.png",
        "alt": "Srila Prabhupada",
    },
}

# Manual card cover images (notion_id -> /assets/filename)
# For pages that don't have Notion cover images
MANUAL_CARD_COVERS = {
    "42bde06312f04b1ba7a3c4887b4af74f": "/assets/manual-del-bhakta-cover.png",
    "364ca98f8f7a4f23a502d7737356d6c8": "/assets/arsa-prayoga-cover.png",
    "37a84db2095e4657ab0a69980134103f": "/assets/arsa-prayoga-cover.png",
    # Blog cards missing covers
    "1a278d504b344dfa9244c7fae44ff2cd": "https://images.unsplash.com/photo-1565060169194-19fabf63012c?w=600&q=80",
    "4add3f0953664561937781f3ebd0af12": "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=600&q=80",
}

# Extra HTML content to append to specific pages (by slug)
CONTENT_APPEND = {
    "/contenido/prabhupada-now/": (
        '<a href="https://a.co/d/09WCi1PA" class="external-link-card" '
        'target="_blank" rel="noopener noreferrer">'
        '<span class="external-link-card__icon">📖</span>'
        '<span class="external-link-card__label">Comprar en Amazon</span>'
        '</a>'
    ),
    "/curso-de-bhakti-yoga/": (
        '<div style="text-align:center">'
        '<a href="https://a.co/d/0dUZk2So" class="external-link-card" '
        'target="_blank" rel="noopener noreferrer">'
        '<span class="external-link-card__icon">📖</span>'
        '<span class="external-link-card__label">Comprar en Amazon</span>'
        '</a>'
        '</div>'
    ),
    "/asistencia/": (
        '<p>📥 <a id="eml" href="#" class="obf-email"></a></p>'
        '<script>'
        '(function(){'
        'var a="info",b="bhaktiyoga",c="es";'
        'var e=a+"@"+b+"."+c;'
        'var el=document.getElementById("eml");'
        'el.href="mai"+"lto:"+e;'
        'el.textContent=e;'
        '})()'
        '</script>'
    ),
}

# Rewrite link hrefs on images by element ID → new URL
IMAGE_LINK_REWRITE = {
    "ca1994d8-f25f-4817-9e2a-08661404e42a": "https://a.co/d/0dUZk2So",
}

# HTML element IDs to remove from specific pages (by slug)
CONTENT_REMOVE_IDS = {
    "/talleres/": ["4a23cf88-d82a-4dba-b179-62dd99fdad86"],
    "/asistencia/": ["bf8eeb85-e882-4f01-8998-9e4463524f60"],
}

# Pages to skip (not public)
SKIP_PAGES = {
    "Se ha recibido tu donativo",
    "Algo ha salido mal con la transacción",
}
