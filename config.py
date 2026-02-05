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
    {
        "label": "Eventos",
        "url": "/eventos/",
        "children": [
            {"label": "Conferencias", "url": "/conferencias/"},
            {"label": "Talleres", "url": "/talleres/"},
            {"label": "Eventos", "url": "/eventos/"},
        ],
    },
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
    "361c82e1b1b7464ab15e16c230a2db53": "/mapa/",
    "2dbe846ade1b428ca98b39027e796313": "/centros/",
}

# Featured portrait images (slug → image path) — floated right beside text
FEATURED_IMAGES = {
    "/a-c-bhaktivedanta-swami-prabhupada/": {
        "src": "/assets/prabhupada.png",
        "alt": "Srila Prabhupada",
    },
}

# Pages to skip (not public)
SKIP_PAGES = {
    "Se ha recibido tu donativo",
    "Algo ha salido mal con la transacción",
}
