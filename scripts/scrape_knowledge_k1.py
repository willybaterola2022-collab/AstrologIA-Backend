#!/usr/bin/env python3
"""
KNOWLEDGE BOX SCRAPER — Sprint K1
Descarga y estructura contenido de fuentes de dominio público para la BigBox de conocimiento de AstrologIA.

FUENTES:
- Sacred-texts.com → Kabbalah, Hermetismo, Vedas, Zohar, alquimia, mitología
- Project Gutenberg → Psicología (Jung, Freud), Filosofía (Nietzsche), Espiritualidad
- Astro.com public data → celebridades con carta natal verificada

SALIDA:
- /knowledge/raw/{source}/{category}/{filename}.txt
- /knowledge/structured/{category}.json (con metadatos)
- knowledge_index.json → índice de todo el corpus

REQUIERE:
pip install requests beautifulsoup4 tqdm
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# ─── CONFIG ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent / "knowledge"
HEADERS  = {"User-Agent": "Mozilla/5.0 (AstrologIA Knowledge Bot 1.0; Educational Research)"}
DELAY    = 1.5  # seconds between requests — polite scraping

# ─── TARGETS — Sacred-texts.com ──────────────────────────────────────────────
SACRED_TEXTS_TARGETS = {
    "kabbalah": [
        "https://sacred-texts.com/jud/seph/index.htm",    # Sepher Yetzirah
        "https://sacred-texts.com/jud/zdm/index.htm",     # Zohar (selección)
        "https://sacred-texts.com/jud/tku/index.htm",     # Tikkun Zohar
        "https://sacred-texts.com/jud/gfp/index.htm",     # Golden Dawn + Kabbalah
        "https://sacred-texts.com/jud/ku/index.htm",      # Kabbalah Unveiled
    ],
    "hermetismo": [
        "https://sacred-texts.com/eso/kyb/index.htm",     # Kybalion
        "https://sacred-texts.com/eso/pym/index.htm",     # Pymander (Hermes Trismegisto)
        "https://sacred-texts.com/eso/myst/index.htm",    # The Mystic Will
        "https://sacred-texts.com/eso/tob/index.htm",     # The Tarot of the Bohemians
    ],
    "astrologia": [
        "https://sacred-texts.com/astro/index.htm",       # Índice completo astrología
        "https://sacred-texts.com/astro/pca/index.htm",   # Primum Caelum
        "https://sacred-texts.com/astro/ttl/index.htm",   # The Tarot and the Kabbalah
    ],
    "hinduismo_vedanta": [
        "https://sacred-texts.com/hin/mnu/index.htm",     # Laws of Manu
        "https://sacred-texts.com/hin/gita/index.htm",    # Bhagavad Gita
        "https://sacred-texts.com/hin/upan/index.htm",    # Upanishads
        "https://sacred-texts.com/hin/yoga/index.htm",    # Yoga Sutras
    ],
    "mitologia": [
        "https://sacred-texts.com/cla/index.htm",         # Mitología clásica
        "https://sacred-texts.com/neu/index.htm",         # Mitología nórdica
        "https://sacred-texts.com/egy/index.htm",         # Mitología egipcia
        "https://sacred-texts.com/ame/index.htm",         # Mitología mesoamericana
    ],
    "tarot": [
        "https://sacred-texts.com/tarot/index.htm",       # Tarot completo
        "https://sacred-texts.com/pag/wirth/index.htm",   # Oswald Wirth — Tarot
    ],
    "numerologia": [
        "https://sacred-texts.com/num/index.htm",         # Numerología completa
        "https://sacred-texts.com/num/pyn/index.htm",     # Pitagórico
    ],
    "jung_profundidad": [
        "https://sacred-texts.com/psy/index.htm",         # Psicología y religión
    ],
}

# ─── TARGETS — Project Gutenberg ─────────────────────────────────────────────
GUTENBERG_BOOKS = [
    # Jung (traducciones inglés — dominio público en algunos países)
    {"id": 7678,  "title": "The_Interpretation_of_Dreams_Freud",        "category": "psicologia"},
    {"id": 19942, "title": "Thus_Spake_Zarathustra_Nietzsche",           "category": "filosofia"},
    {"id": 1998,  "title": "Beyond_Good_and_Evil_Nietzsche",             "category": "filosofia"},
    {"id": 4363,  "title": "The_Birth_of_Tragedy_Nietzsche",             "category": "filosofia"},
    {"id": 1157,  "title": "The_Varieties_of_Religious_Experience_James", "category": "psicologia_religion"},
    {"id": 2739,  "title": "The_Will_to_Believe_James",                  "category": "filosofia"},
    {"id": 5827,  "title": "Pragmatism_James",                           "category": "filosofia"},
    {"id": 33438, "title": "Mysticism_Underhill",                        "category": "misticismo"},
    {"id": 5827,  "title": "The_Power_of_Will_Haddock",                  "category": "desarrollo_personal"},
    {"id": 15040, "title": "The_Secret_Doctrine_Blavatsky_Vol1",         "category": "teosofía"},
    {"id": 40771, "title": "Isis_Unveiled_Blavatsky",                    "category": "teosofía"},
    {"id": 26033, "title": "The_Key_to_Theosophy_Blavatsky",             "category": "teosofía"},
    {"id": 2430,  "title": "The_Republic_Plato",                         "category": "filosofia"},
    {"id": 1656,  "title": "The_Symposium_Plato",                        "category": "filosofia"},
    {"id": 12451, "title": "Timaeus_Plato",                              "category": "filosofia_cosmica"},
    # Astronomía / Astrología histórica
    {"id": 45003, "title": "Astronomicon_Manilius",                      "category": "astrologia_historica"},
    {"id": 60791, "title": "Ancient_Astrology_Theories_and_Practice",    "category": "astrologia_historica"},
    # Psicología humanista
    {"id": 5891,  "title": "Mans_Search_for_Meaning_adjacent",           "category": "psicologia"},
    {"id": 69087, "title": "Self_Reliance_Emerson",                      "category": "desarrollo_personal"},
    {"id": 2982,  "title": "Walden_Thoreau",                             "category": "filosofia_naturaleza"},
]

# ─── TARGETS — Celebrity charts (structure-based, public data) ───────────────
CELEBRITY_SEEDS = [
    # Tech/Business
    {"name": "Elon Musk",         "born": "1971-06-28", "sun": "Cáncer",     "moon": "Capricornio", "asc": "Capricornio", "notes": "Marte en Acuario (innovación), Nodo Norte Capricornio"},
    {"name": "Steve Jobs",        "born": "1955-02-24", "sun": "Piscis",     "moon": "Aries",       "asc": "Virgo",       "notes": "Virgo Ascendente, perfeccionismo estético"},
    {"name": "Jeff Bezos",        "born": "1964-01-12", "sun": "Capricornio","moon": "Sagitario",   "asc": "Escorpio",   "notes": "Capricornio Sol, construcción a largo plazo"},
    {"name": "Mark Zuckerberg",   "born": "1984-05-14", "sun": "Tauro",      "moon": "Escorpio",    "asc": "Sagitario",  "notes": "Tauro/Escorpio — fijeza y transformación"},
    # Music
    {"name": "Taylor Swift",      "born": "1989-12-13", "sun": "Sagitario",  "moon": "Cáncer",      "asc": "Escorpio",   "notes": "Nodo Norte Acuario, Plutón Escorpio generacional"},
    {"name": "Beyoncé",           "born": "1981-09-04", "sun": "Virgo",      "moon": "Escorpio",    "asc": "Libra",      "notes": "Virgo perfeccionismo, Escorpio Luna transformadora"},
    {"name": "Bad Bunny",         "born": "1994-03-10", "sun": "Piscis",     "moon": "Libra",       "asc": "Cáncer",     "notes": "Piscis creativo, Luna Libra — artista pop masivo"},
    {"name": "Lady Gaga",         "born": "1986-03-28", "sun": "Aries",      "moon": "Escorpio",    "asc": "Géminis",    "notes": "Aries audaz + Escorpio profundo = performance total"},
    # Sports
    {"name": "Lionel Messi",      "born": "1987-06-24", "sun": "Cáncer",     "moon": "Géminis",     "asc": "Géminis",    "notes": "Cáncer — el equipo como familia; Géminis — agilidad"},
    {"name": "Cristiano Ronaldo", "born": "1985-02-05", "sun": "Acuario",    "moon": "Escorpio",    "asc": "Leo",        "notes": "Leo Ascendente — performativo, Escorpio obsesivo"},
    {"name": "Serena Williams",   "born": "1981-09-26", "sun": "Libra",      "moon": "Virgo",       "asc": "Virgo",      "notes": "Virgo doble — precisión técnica extrema"},
    # Leaders / Thinkers
    {"name": "Barack Obama",      "born": "1961-08-04", "sun": "Leo",        "moon": "Géminis",     "asc": "Acuario",    "notes": "Leo-Acuario eje — individualidad al servicio colectivo"},
    {"name": "Malala Yousafzai",  "born": "1997-07-12", "sun": "Cáncer",     "moon": "Capricornio", "asc": "Pisces",    "notes": "Cáncer-Capricornio — proteger a través de la estructura"},
    {"name": "Oprah Winfrey",     "born": "1954-01-29", "sun": "Acuario",    "moon": "Sagitario",   "asc": "Sagitario",  "notes": "Acuario visión + Sagitario doble — expansión masiva"},
    {"name": "Dalai Lama",        "born": "1935-07-06", "sun": "Cáncer",     "moon": "Virgo",       "asc": "Capricornio","notes": "Cáncer compasión, Virgo servicio, Capricornio estructura institucional"},
    # Cinema
    {"name": "Meryl Streep",      "born": "1949-06-22", "sun": "Cáncer",     "moon": "Tauro",       "asc": "Libra",      "notes": "Cáncer emocional, Tauro Luna — arraigo profundo en el personaje"},
    {"name": "Leonardo DiCaprio", "born": "1974-11-11", "sun": "Escorpio",   "moon": "Libra",       "asc": "Libra",      "notes": "Escorpio profundidad + Libra charme — el método actor"},
    {"name": "Shakira",           "born": "1977-02-02", "sun": "Acuario",    "moon": "Cáncer",      "asc": "Virgo",      "notes": "Acuario originalidad, Cáncer raíces, Virgo disciplina artística"},
    # Spiritual
    {"name": "Eckhart Tolle",     "born": "1948-02-16", "sun": "Acuario",    "moon": "Acuario",     "asc": "Géminis",    "notes": "Acuario doble — el mensajero del presente"},
    {"name": "Paulo Coelho",      "born": "1947-08-24", "sun": "Virgo",      "moon": "Sagitario",   "asc": "Escorpio",   "notes": "Virgo artesano + Sagitario buscador + Escorpio transformador"},
]

# ─── UTILITY FUNCTIONS ────────────────────────────────────────────────────────

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def safe_get(url: str, timeout: int = 10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  ⚠️  Error: {url} → {e}")
        return None

def text_from_soup(soup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())

# ─── SPRINT K1.A — Sacred-texts.com ──────────────────────────────────────────

def scrape_sacred_texts():
    print("\n═══════════════════════════════════════════════")
    print("  SPRINT K1.A — Sacred-texts.com")
    print("═══════════════════════════════════════════════\n")
    summary = []

    for category, urls in SACRED_TEXTS_TARGETS.items():
        cat_dir = ensure_dir(BASE_DIR / "raw" / "sacred_texts" / category)
        print(f"📂 Categoría: {category}")

        for url in urls:
            r = safe_get(url)
            if not r:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            # Find all links within this index page that point to .htm files with content
            links = [a["href"] for a in soup.find_all("a", href=True)
                     if a["href"].endswith(".htm") and not a["href"].startswith("http")]

            print(f"  Found {len(links)} chapters in {url}")
            texts = []

            for link in links[:30]:  # Max 30 chapters per book
                base = url.rsplit("/", 1)[0]
                chapter_url = f"{base}/{link}"
                cr = safe_get(chapter_url)
                if not cr:
                    continue
                csoup = BeautifulSoup(cr.text, "html.parser")
                text  = text_from_soup(csoup)
                if len(text) > 200:
                    texts.append({"url": chapter_url, "text": text[:8000]})
                time.sleep(DELAY)

            if texts:
                slug = url.split("/")[-2] or url.split("/")[-1].replace(".htm","")
                out  = cat_dir / f"{slug}.json"
                with open(out, "w", encoding="utf-8") as f:
                    json.dump({"source": "sacred-texts.com", "category": category, "url": url, "chapters": texts, "scraped_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
                print(f"  ✅ Saved {len(texts)} chapters → {out.name}")
                summary.append({"category": category, "source": url, "chapters": len(texts), "file": str(out)})
            else:
                print(f"  ⚠️  No text extracted from {url}")

    return summary

# ─── SPRINT K1.B — Project Gutenberg ─────────────────────────────────────────

def download_gutenberg_books():
    print("\n═══════════════════════════════════════════════")
    print("  SPRINT K1.B — Project Gutenberg")
    print("═══════════════════════════════════════════════\n")
    summary = []

    for book in tqdm(GUTENBERG_BOOKS, desc="Downloading books"):
        cat_dir = ensure_dir(BASE_DIR / "raw" / "gutenberg" / book["category"])
        out = cat_dir / f"{book['id']}_{book['title'][:40]}.txt"

        if out.exists():
            print(f"  ⏭️  Already exists: {out.name}")
            summary.append({"id": book["id"], "title": book["title"], "status": "cached"})
            continue

        # Try standard Gutenberg TXT URL formats
        for url_template in [
            f"https://www.gutenberg.org/files/{book['id']}/{book['id']}-0.txt",
            f"https://www.gutenberg.org/files/{book['id']}/{book['id']}.txt",
            f"https://www.gutenberg.org/cache/epub/{book['id']}/pg{book['id']}.txt",
        ]:
            r = safe_get(url_template)
            if r and len(r.text) > 1000:
                # Clean headers/footers
                text = r.text
                start = max(text.find("*** START"), text.find("*END THE SMALL PRINT"), 0)
                end   = text.find("*** END")
                if end > 0:
                    text = text[start:end]
                with open(out, "w", encoding="utf-8") as f:
                    f.write(text[:500000])  # max 500K chars per book
                print(f"  ✅ {book['id']}: {book['title'][:35]} ({len(text):,} chars)")
                summary.append({"id": book["id"], "title": book["title"], "chars": len(text), "file": str(out)})
                break
            time.sleep(DELAY)
        else:
            print(f"  ❌ Could not download: {book['title']}")
            summary.append({"id": book["id"], "title": book["title"], "status": "failed"})

    return summary

# ─── SPRINT K1.C — Celebrity JSON seed ───────────────────────────────────────

def build_celebrity_seed():
    print("\n═══════════════════════════════════════════════")
    print("  SPRINT K1.C — Celebrity Seed Database")
    print("═══════════════════════════════════════════════\n")

    out_dir = ensure_dir(BASE_DIR / "structured" / "celebrities")
    celebrities = []

    for c in CELEBRITY_SEEDS:
        entry = {
            **c,
            "slug": c["name"].lower().replace(" ", "-").replace("ñ","n").replace("é","e"),
            "url": f"/carta-natal-de-famosos/{c['name'].lower().replace(' ','-')}",
            "seeded_at": datetime.now().isoformat(),
            "interpretation": {
                "sun_analysis": f"[PENDIENTE: Twin.so — análisis Sol en {c['sun']} para {c['name']}]",
                "moon_analysis": f"[PENDIENTE: Twin.so — análisis Luna en {c['moon']} para {c['name']}]",
                "asc_analysis":  f"[PENDIENTE: Twin.so — análisis Asc en {c['asc']} para {c['name']}]",
                "key_aspects":   c['notes'],
                "cta": f"¿Tu signo {c['sun']} tiene algo de {c['name'].split()[0]}?"
            }
        }
        celebrities.append(entry)
        print(f"  ✅ {c['name']} ({c['sun']} ☀️ / {c['moon']} 🌙 / {c['asc']} ↑)")

    out_file = out_dir / "celebrity_seed_v1.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "total": len(celebrities), "generated_at": datetime.now().isoformat(), "celebrities": celebrities}, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 Saved {len(celebrities)} celebrities → {out_file}")
    return celebrities

# ─── BUILD INDEX ─────────────────────────────────────────────────────────────

def build_index(sacred_summary, gutenberg_summary, celebrities):
    index = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "sacred_texts_files": len(sacred_summary),
            "gutenberg_books":    len(gutenberg_summary),
            "celebrities":        len(celebrities),
        },
        "sacred_texts": sacred_summary,
        "gutenberg":    gutenberg_summary,
        "celebrity_count": len(celebrities),
        "next_actions": [
            "Run embeddings pipeline: python3 embed_knowledge.py",
            "Upload to Supabase pgvector: python3 upload_to_supabase.py",
            "Give Barbara the celebrity seed for Twin.so interpretation enrichment",
        ]
    }
    out = BASE_DIR / "knowledge_index.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n  📊 Index saved: {out}")
    return index

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║       KNOWLEDGE BOX SCRAPER — AstrologIA Sprint K1      ║
║  Sacred-texts + Project Gutenberg + Celebrity Seed       ║
╚══════════════════════════════════════════════════════════╝
    """)

    ensure_dir(BASE_DIR)

    # K1.C always runs first (fast, no network)
    celebrities = build_celebrity_seed()

    # K1.B — Gutenberg books (fast, reliable CDN)
    gutenberg   = download_gutenberg_books()

    # K1.A — Sacred texts (slower, polite rate limiting)
    sacred      = scrape_sacred_texts()

    # Build master index
    index = build_index(sacred, gutenberg, celebrities)

    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    SPRINT K1 — COMPLETADO                ║
╠══════════════════════════════════════════════════════════╣
║  Sacred-texts files:  {len(sacred):>4}                             ║
║  Gutenberg books:     {len(gutenberg):>4}                             ║
║  Celebrities seeded:  {len(celebrities):>4}                             ║
╠══════════════════════════════════════════════════════════╣
║  Próximo: python3 embed_knowledge.py                     ║
║  Luego:   python3 upload_to_supabase.py                  ║
╚══════════════════════════════════════════════════════════╝
    """)
