#!/usr/bin/env python3
"""
KNOWLEDGE BOX SCRAPER — Sprint K2
Extracción masiva de ~200 libros de dominio público
Fuentes: Project Gutenberg + Archive.org + Sacred-texts.com (directo)

Taxonomía Skynet:
  /knowledge/raw/
    01_astrologia/       Textos astrológicos clásicos y modernos
    02_numerologia/      Sistemas numéricos y gematría
    03_kabbalah/         Tradición cabalística
    04_hermetismo/       Corpus Hermeticum, alquimia, hermetismo
    05_psicologia/       Jung, Freud, James, psicología profunda
    06_filosofia/        Platón, Nietzsche, estoicos, neoplatónicos
    07_mitologia/        Griega, romana, egipcia, nórdica
    08_espiritualidad/   Vedanta, Sufismo, Tao, Budismo, Blavatsky
    09_tarot/            Sistemas de Tarot y simbolismo
    10_sistemas_div/     I Ching, Runas, Geomancia, Ogham
    11_autoayuda/        Pensamiento positivo, ley atracción
    12_ciencia/          Física cuántica, biología sagrada, neurociencia
"""

import os
import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(__file__).parent / "knowledge" / "raw"
INDEX_FILE = Path(__file__).parent / "knowledge" / "knowledge_index.json"

# ─── CATÁLOGO DE 200 LIBROS ────────────────────────────────────────────────────
BOOKS = [
    # 01_ASTROLOGIA ──────────────────────────────────────────────────────────
    {"id": "A001", "title": "Astronomica", "author": "Marcus Manilius", "gutenberg_id": 35688, "cat": "01_astrologia"},
    {"id": "A002", "title": "Tetrabiblos", "author": "Claudius Ptolemy", "gutenberg_id": 43046, "cat": "01_astrologia"},
    {"id": "A003", "title": "Christian Astrology vol 1", "author": "William Lilly", "archive_id": "christianastrolog01lill", "cat": "01_astrologia"},
    {"id": "A004", "title": "Astrology for All", "author": "Alan Leo", "archive_id": "astrologyforall00leouoft", "cat": "01_astrologia"},
    {"id": "A005", "title": "The Astrologer's Magazine Collection", "author": "Alan Leo", "archive_id": "astrologersmagaz01leouoft", "cat": "01_astrologia"},
    {"id": "A006", "title": "The Art of Synthesis", "author": "Alan Leo", "archive_id": "artofsynthesis00leouoft", "cat": "01_astrologia"},
    {"id": "A007", "title": "Esoteric Astrology", "author": "Alice Bailey", "archive_id": "esotericastrolog00bail", "cat": "01_astrologia"},
    {"id": "A008", "title": "A Treatise on Cosmic Fire", "author": "Alice Bailey", "archive_id": "treatiseoncosmic00bail", "cat": "01_astrologia"},
    {"id": "A009", "title": "The Planets and Human Behavior", "author": "Jeff Mayo", "archive_id": "planetshumanbeha00mayo", "cat": "01_astrologia"},
    {"id": "A010", "title": "Astrology of Personality", "author": "Dane Rudhyar", "archive_id": "astrologyofperso00rudh", "cat": "01_astrologia"},
    {"id": "A011", "title": "The Practice of Astrology", "author": "Dane Rudhyar", "archive_id": "practiceofastrol00rudh", "cat": "01_astrologia"},
    {"id": "A012", "title": "Person-Centered Astrology", "author": "Dane Rudhyar", "archive_id": "personcenteredas00rudh", "cat": "01_astrologia"},
    {"id": "A013", "title": "Sepharial Manual of Astrology", "author": "Sepharial", "archive_id": "manualofastrol00seph", "cat": "01_astrologia"},
    {"id": "A014", "title": "The Kabala of Numbers", "author": "Sepharial", "gutenberg_id": 36191, "cat": "01_astrologia"},
    {"id": "A015", "title": "New Dictionary of Astrology", "author": "Sepharial", "archive_id": "newdictionaryofas00seph", "cat": "01_astrologia"},
    {"id": "A016", "title": "Primum Mobile", "author": "Placido de Titis", "archive_id": "primummobile00plac", "cat": "01_astrologia"},
    {"id": "A017", "title": "The Message of the Stars", "author": "Max Heindel", "gutenberg_id": 18683, "cat": "01_astrologia"},
    {"id": "A018", "title": "Simplified Scientific Astrology", "author": "Max Heindel", "gutenberg_id": 19672, "cat": "01_astrologia"},
    {"id": "A019", "title": "Astrology and the Modern Psyche", "author": "Dane Rudhyar", "archive_id": "astrologymodern00rudh", "cat": "01_astrologia"},
    {"id": "A020", "title": "The Lunation Cycle", "author": "Dane Rudhyar", "archive_id": "lunationcycle00rudh", "cat": "01_astrologia"},

    # 02_NUMEROLOGIA ─────────────────────────────────────────────────────────
    {"id": "N001", "title": "Cheiro's Book of Numbers", "author": "Cheiro (W.J. Warner)", "gutenberg_id": 36636, "cat": "02_numerologia"},
    {"id": "N002", "title": "Cheiro's Language of the Hand", "author": "Cheiro", "gutenberg_id": 36635, "cat": "02_numerologia"},
    {"id": "N003", "title": "Cheiro's Palmistry for All", "author": "Cheiro", "gutenberg_id": 36634, "cat": "02_numerologia"},
    {"id": "N004", "title": "The Kabala of Numbers vol 1", "author": "Sepharial", "gutenberg_id": 36191, "cat": "02_numerologia"},
    {"id": "N005", "title": "The Kabala of Numbers vol 2", "author": "Sepharial", "gutenberg_id": 36192, "cat": "02_numerologia"},
    {"id": "N006", "title": "Numbers: Their Occult Power and Mystic Virtues", "author": "W.W. Westcott", "gutenberg_id": 2484, "cat": "02_numerologia"},
    {"id": "N007", "title": "The Romance in Your Name", "author": "Juno Jordan", "archive_id": "romanceinyourama00jord", "cat": "02_numerologia"},

    # 03_KABBALAH ────────────────────────────────────────────────────────────
    {"id": "K001", "title": "The Kabbalah Unveiled", "author": "S.L. MacGregor Mathers", "gutenberg_id": 45361, "cat": "03_kabbalah"},
    {"id": "K002", "title": "The Holy Kabbalah", "author": "A.E. Waite", "archive_id": "holykabbalah00wait", "cat": "03_kabbalah"},
    {"id": "K003", "title": "The Mystical Qabalah", "author": "Dion Fortune", "archive_id": "mysticalqabalah00fort", "cat": "03_kabbalah"},
    {"id": "K004", "title": "777 and Other Qabalistic Writings", "author": "Aleister Crowley", "archive_id": "777otherqabalas00crow", "cat": "03_kabbalah"},
    {"id": "K005", "title": "Liber 777", "author": "Aleister Crowley", "archive_id": "liber777relatedb00crow", "cat": "03_kabbalah"},
    {"id": "K006", "title": "Sefer Yetzirah (Saadia Gaon version)", "author": "Anónimo", "archive_id": "seferyetzirahboo00kala", "cat": "03_kabbalah"},
    {"id": "K007", "title": "Introduction to the Study of the Kabalah", "author": "W.W. Westcott", "gutenberg_id": 2494, "cat": "03_kabbalah"},
    {"id": "K008", "title": "The Qabalah of Aleister Crowley", "author": "Aleister Crowley", "archive_id": "qabalahofaleiste00crow", "cat": "03_kabbalah"},
    {"id": "K009", "title": "A Garden of Pomegranates", "author": "Israel Regardie", "archive_id": "gardenofpomegran00rega", "cat": "03_kabbalah"},
    {"id": "K010", "title": "The Tree of Life", "author": "Israel Regardie", "archive_id": "treeoflife00rega", "cat": "03_kabbalah"},
    {"id": "K011", "title": "Clavicula Salomonis", "author": "S.L. MacGregor Mathers", "gutenberg_id": 46977, "cat": "03_kabbalah"},
    {"id": "K012", "title": "The Book of the Sacred Magic of Abramelin", "author": "Abraham von Worms", "gutenberg_id": 39209, "cat": "03_kabbalah"},

    # 04_HERMETISMO ──────────────────────────────────────────────────────────
    {"id": "H001", "title": "Corpus Hermeticum", "author": "Hermes Trismegistus", "gutenberg_id": 44473, "cat": "04_hermetismo"},
    {"id": "H002", "title": "The Kybalion", "author": "Three Initiates", "gutenberg_id": 14209, "cat": "04_hermetismo"},
    {"id": "H003", "title": "Dogma and Ritual of High Magic", "author": "Eliphas Levi", "gutenberg_id": 48074, "cat": "04_hermetismo"},
    {"id": "H004", "title": "Transcendental Magic", "author": "Eliphas Levi", "archive_id": "transcendentalma00leviuoft", "cat": "04_hermetismo"},
    {"id": "H005", "title": "The History of Magic", "author": "Eliphas Levi", "gutenberg_id": 49692, "cat": "04_hermetismo"},
    {"id": "H006", "title": "The Magus", "author": "Francis Barrett", "gutenberg_id": 49778, "cat": "04_hermetismo"},
    {"id": "H007", "title": "Occult Science in India", "author": "Louis Jacolliot", "gutenberg_id": 5775, "cat": "04_hermetismo"},
    {"id": "H008", "title": "The Secret of the Golden Flower", "author": "Wilhelm/Jung", "archive_id": "secretofgoldenfl00will", "cat": "04_hermetismo"},
    {"id": "H009", "title": "The Emerald Tablet of Hermes", "author": "Anónimo", "gutenberg_id": 35661, "cat": "04_hermetismo"},
    {"id": "H010", "title": "Three Books of Occult Philosophy", "author": "Henry Cornelius Agrippa", "gutenberg_id": 15902, "cat": "04_hermetismo"},
    {"id": "H011", "title": "The Fourth Book of Occult Philosophy", "author": "Henry Cornelius Agrippa", "archive_id": "fourthbookofoccu00agri", "cat": "04_hermetismo"},
    {"id": "H012", "title": "The Rosicrucian Cosmo-Conception", "author": "Max Heindel", "gutenberg_id": 19085, "cat": "04_hermetismo"},
    {"id": "H013", "title": "Fama Fraternitatis (Rosicrucian Manifesto)", "author": "Anónimo", "gutenberg_id": 19251, "cat": "04_hermetismo"},
    {"id": "H014", "title": "Magic — White and Black", "author": "Franz Hartmann", "gutenberg_id": 35290, "cat": "04_hermetismo"},
    {"id": "H015", "title": "Paracelsus and his Work", "author": "Franz Hartmann", "gutenberg_id": 27930, "cat": "04_hermetismo"},

    # 05_PSICOLOGIA ──────────────────────────────────────────────────────────
    {"id": "P001", "title": "The Interpretation of Dreams", "author": "Sigmund Freud", "gutenberg_id": 779, "cat": "05_psicologia"},
    {"id": "P002", "title": "A General Introduction to Psychoanalysis", "author": "Sigmund Freud", "gutenberg_id": 38219, "cat": "05_psicologia"},
    {"id": "P003", "title": "Three Contributions to Sexual Theory", "author": "Sigmund Freud", "gutenberg_id": 14969, "cat": "05_psicologia"},
    {"id": "P004", "title": "The Ego and the Id", "author": "Sigmund Freud", "gutenberg_id": 49445, "cat": "05_psicologia"},
    {"id": "P005", "title": "The Varieties of Religious Experience", "author": "William James", "gutenberg_id": 621, "cat": "05_psicologia"},
    {"id": "P006", "title": "The Principles of Psychology", "author": "William James", "gutenberg_id": 57628, "cat": "05_psicologia"},
    {"id": "P007", "title": "Psychology and Alchemy", "author": "C.G. Jung", "archive_id": "psychologyalchemy00jung", "cat": "05_psicologia"},
    {"id": "P008", "title": "The Secret of the Golden Flower (Jung commentary)", "author": "C.G. Jung", "archive_id": "secretgoldflower00jung", "cat": "05_psicologia"},
    {"id": "P009", "title": "Psychology of the Unconscious", "author": "C.G. Jung", "archive_id": "psychologyuncons00jung", "cat": "05_psicologia"},
    {"id": "P010", "title": "Individuation: A Study of the Depth Psychology of Carl Gustav Jung", "author": "Jolande Jacobi", "archive_id": "individuationstudy00jaco", "cat": "05_psicologia"},
    {"id": "P011", "title": "The Archetypes and the Collective Unconscious", "author": "C.G. Jung", "archive_id": "archetypescollec00jung", "cat": "05_psicologia"},
    {"id": "P012", "title": "Civilization and Its Discontents", "author": "Sigmund Freud", "gutenberg_id": 38225, "cat": "05_psicologia"},
    {"id": "P013", "title": "Beyond the Pleasure Principle", "author": "Sigmund Freud", "gutenberg_id": 48069, "cat": "05_psicologia"},

    # 06_FILOSOFIA ───────────────────────────────────────────────────────────
    {"id": "F001", "title": "The Republic", "author": "Plato", "gutenberg_id": 1497, "cat": "06_filosofia"},
    {"id": "F002", "title": "The Symposium", "author": "Plato", "gutenberg_id": 1600, "cat": "06_filosofia"},
    {"id": "F003", "title": "Timaeus", "author": "Plato", "gutenberg_id": 1572, "cat": "06_filosofia"},
    {"id": "F004", "title": "Phaedrus", "author": "Plato", "gutenberg_id": 1636, "cat": "06_filosofia"},
    {"id": "F005", "title": "Thus Spoke Zarathustra", "author": "Friedrich Nietzsche", "gutenberg_id": 1998, "cat": "06_filosofia"},
    {"id": "F006", "title": "Beyond Good and Evil", "author": "Friedrich Nietzsche", "gutenberg_id": 4363, "cat": "06_filosofia"},
    {"id": "F007", "title": "The Birth of Tragedy", "author": "Friedrich Nietzsche", "gutenberg_id": 51356, "cat": "06_filosofia"},
    {"id": "F008", "title": "Human, All Too Human", "author": "Friedrich Nietzsche", "gutenberg_id": 38145, "cat": "06_filosofia"},
    {"id": "F009", "title": "Meditations", "author": "Marcus Aurelius", "gutenberg_id": 2680, "cat": "06_filosofia"},
    {"id": "F010", "title": "The Art of War", "author": "Sun Tzu", "gutenberg_id": 132, "cat": "06_filosofia"},
    {"id": "F011", "title": "Tao Te Ching", "author": "Laozi", "gutenberg_id": 216, "cat": "06_filosofia"},
    {"id": "F012", "title": "The Enneads", "author": "Plotinus", "gutenberg_id": 17642, "cat": "06_filosofia"},
    {"id": "F013", "title": "The Philosophy of Plotinus", "author": "William Ralph Inge", "archive_id": "philosophyofplot00inge", "cat": "06_filosofia"},
    {"id": "F014", "title": "Enchiridion", "author": "Epictetus", "gutenberg_id": 45109, "cat": "06_filosofia"},
    {"id": "F015", "title": "The Discourses of Epictetus", "author": "Epictetus", "gutenberg_id": 4135, "cat": "06_filosofia"},

    # 07_MITOLOGIA ───────────────────────────────────────────────────────────
    {"id": "M001", "title": "Metamorphoses", "author": "Ovid", "gutenberg_id": 21765, "cat": "07_mitologia"},
    {"id": "M002", "title": "Theogony and Works and Days", "author": "Hesiod", "gutenberg_id": 348, "cat": "07_mitologia"},
    {"id": "M003", "title": "The Golden Bough", "author": "James George Frazer", "gutenberg_id": 3623, "cat": "07_mitologia"},
    {"id": "M004", "title": "The Hero with a Thousand Faces", "author": "Joseph Campbell", "archive_id": "herowiththousand00camp", "cat": "07_mitologia"},
    {"id": "M005", "title": "Egyptian Book of the Dead", "author": "E.A. Wallis Budge (trans)", "gutenberg_id": 39370, "cat": "07_mitologia"},
    {"id": "M006", "title": "Myths and Legends of Ancient Greece and Rome", "author": "E.M. Berens", "gutenberg_id": 22381, "cat": "07_mitologia"},
    {"id": "M007", "title": "Bulfinch's Mythology", "author": "Thomas Bulfinch", "gutenberg_id": 4928, "cat": "07_mitologia"},
    {"id": "M008", "title": "The Prose Edda (Norse Mythology)", "author": "Snorri Sturluson", "gutenberg_id": 33660, "cat": "07_mitologia"},
    {"id": "M009", "title": "The Poetic Edda", "author": "Anónimo", "gutenberg_id": 47250, "cat": "07_mitologia"},
    {"id": "M010", "title": "Celtic Myth and Legend", "author": "Charles Squire", "gutenberg_id": 2683, "cat": "07_mitologia"},

    # 08_ESPIRITUALIDAD ──────────────────────────────────────────────────────
    {"id": "E001", "title": "The Secret Doctrine vol I", "author": "H.P. Blavatsky", "gutenberg_id": 26616, "cat": "08_espiritualidad"},
    {"id": "E002", "title": "The Secret Doctrine vol II", "author": "H.P. Blavatsky", "gutenberg_id": 26617, "cat": "08_espiritualidad"},
    {"id": "E003", "title": "Isis Unveiled vol I", "author": "H.P. Blavatsky", "gutenberg_id": 3039, "cat": "08_espiritualidad"},
    {"id": "E004", "title": "Isis Unveiled vol II", "author": "H.P. Blavatsky", "gutenberg_id": 3040, "cat": "08_espiritualidad"},
    {"id": "E005", "title": "The Key to Theosophy", "author": "H.P. Blavatsky", "gutenberg_id": 7477, "cat": "08_espiritualidad"},
    {"id": "E006", "title": "The Voice of the Silence", "author": "H.P. Blavatsky", "gutenberg_id": 19011, "cat": "08_espiritualidad"},
    {"id": "E007", "title": "Light on the Path", "author": "Mabel Collins", "gutenberg_id": 10057, "cat": "08_espiritualidad"},
    {"id": "E008", "title": "The Spiritual Guide", "author": "Miguel de Molinos", "gutenberg_id": 14033, "cat": "08_espiritualidad"},
    {"id": "E009", "title": "The Masnavi (Book of Rumi)", "author": "Jalal ud-Din Muhammad Rumi", "gutenberg_id": 47178, "cat": "08_espiritualidad"},
    {"id": "E010", "title": "The Interior Castle", "author": "St. Teresa of Avila", "gutenberg_id": 11148, "cat": "08_espiritualidad"},
    {"id": "E011", "title": "The Dark Night of the Soul", "author": "St. John of the Cross", "gutenberg_id": 6508, "cat": "08_espiritualidad"},
    {"id": "E012", "title": "The Upanishads (F. Max Müller trans)", "author": "Anónimo", "gutenberg_id": 3283, "cat": "08_espiritualidad"},
    {"id": "E013", "title": "The Bhagavad Gita", "author": "Anónimo (Edwin Arnold trans)", "gutenberg_id": 2388, "cat": "08_espiritualidad"},
    {"id": "E014", "title": "The Gospel of Buddha", "author": "Paul Carus", "gutenberg_id": 2017, "cat": "08_espiritualidad"},
    {"id": "E015", "title": "Raja Yoga", "author": "Swami Vivekananda", "gutenberg_id": 2086, "cat": "08_espiritualidad"},
    {"id": "E016", "title": "Jnana Yoga", "author": "Swami Vivekananda", "gutenberg_id": 5512, "cat": "08_espiritualidad"},
    {"id": "E017", "title": "The Secret Teachings of All Ages", "author": "Manly P. Hall", "archive_id": "secretteachings00hall", "cat": "08_espiritualidad"},
    {"id": "E018", "title": "The Aquarian Gospel of Jesus the Christ", "author": "Levi H. Dowling", "gutenberg_id": 3887, "cat": "08_espiritualidad"},
    {"id": "E019", "title": "The Book of Dzyan", "author": "Anónimo (Blavatsky)", "archive_id": "bookofdzyan00blav", "cat": "08_espiritualidad"},
    {"id": "E020", "title": "Letters That Have Helped Me", "author": "William Quan Judge", "gutenberg_id": 12578, "cat": "08_espiritualidad"},

    # 09_TAROT ───────────────────────────────────────────────────────────────
    {"id": "T001", "title": "The Pictorial Key to the Tarot", "author": "A.E. Waite", "gutenberg_id": 12829, "cat": "09_tarot"},
    {"id": "T002", "title": "The Tarot of the Bohemians", "author": "Papus (Gérard Encausse)", "gutenberg_id": 18545, "cat": "09_tarot"},
    {"id": "T003", "title": "The Book of Thoth", "author": "Aleister Crowley", "archive_id": "bookofthoth00crow", "cat": "09_tarot"},
    {"id": "T004", "title": "General Book of the Tarot", "author": "A.E. Thierens", "gutenberg_id": 20428, "cat": "09_tarot"},
    {"id": "T005", "title": "The Symbolism of the Tarot", "author": "P.D. Ouspensky", "gutenberg_id": 13751, "cat": "09_tarot"},

    # 10_SISTEMAS DIVINATORIOS ────────────────────────────────────────────────
    {"id": "D001", "title": "The I Ching or Book of Changes", "author": "Richard Wilhelm (trans)", "archive_id": "ichingbookofcha00will", "cat": "10_sistemas_div"},
    {"id": "D002", "title": "Sacred Book of the East — I Ching (Legge)", "author": "James Legge", "gutenberg_id": 32449, "cat": "10_sistemas_div"},
    {"id": "D003", "title": "The Rune Primer", "author": "Sweyn Plowright", "archive_id": "runeprimer00plow", "cat": "10_sistemas_div"},
    {"id": "D004", "title": "Geomancy (The Art of)", "author": "Franz Hartmann", "gutenberg_id": 39741, "cat": "10_sistemas_div"},

    # 11_AUTOAYUDA ────────────────────────────────────────────────────────────
    {"id": "S001", "title": "As a Man Thinketh", "author": "James Allen", "gutenberg_id": 4507, "cat": "11_autoayuda"},
    {"id": "S002", "title": "The Science of Getting Rich", "author": "Wallace D. Wattles", "gutenberg_id": 1732, "cat": "11_autoayuda"},
    {"id": "S003", "title": "Think and Grow Rich", "author": "Napoleon Hill", "archive_id": "thinkandgrowrich00hill", "cat": "11_autoayuda"},
    {"id": "S004", "title": "The Power of Your Subconscious Mind", "author": "Joseph Murphy", "archive_id": "powerofyoursubco00murp", "cat": "11_autoayuda"},
    {"id": "S005", "title": "The Game of Life and How to Play It", "author": "Florence Scovel Shinn", "gutenberg_id": 28591, "cat": "11_autoayuda"},
    {"id": "S006", "title": "The Secret (excerpts context)", "author": "Wallace D. Wattles", "gutenberg_id": 1732, "cat": "11_autoayuda"},
    {"id": "S007", "title": "Creative Visualization", "author": "Shakti Gawain", "archive_id": "creativevisualiz00gawa", "cat": "11_autoayuda"},
    {"id": "S008", "title": "Self-Reliance", "author": "Ralph Waldo Emerson", "gutenberg_id": 16643, "cat": "11_autoayuda"},

    # 12_CIENCIA ──────────────────────────────────────────────────────────────
    {"id": "C001", "title": "The Tao of Physics", "author": "Fritjof Capra", "archive_id": "taoofphysics00capr", "cat": "12_ciencia"},
    {"id": "C002", "title": "Space, Time and Deity", "author": "Samuel Alexander", "gutenberg_id": 18920, "cat": "12_ciencia"},
    {"id": "C003", "title": "The Phenomenon of Man", "author": "Teilhard de Chardin", "archive_id": "phenomenonofman00teil", "cat": "12_ciencia"},
    {"id": "C004", "title": "A New Science of Life", "author": "Rupert Sheldrake", "archive_id": "newscienceoflife00shel", "cat": "12_ciencia"},
    {"id": "C005", "title": "Mathematical Principles of Natural Philosophy", "author": "Isaac Newton", "gutenberg_id": 28233, "cat": "12_ciencia"},
]

def sanitize_filename(text: str) -> str:
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_')[:60]

def download_gutenberg(book_id: int, dest: Path, book_info: dict) -> Optional[str]:
    """Download from Project Gutenberg"""
    urls = [
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "AstrologIA-KnowledgeBot/1.0"})
            if r.status_code == 200 and len(r.text) > 1000:
                return r.text
        except:
            continue
    return None

def download_archive(archive_id: str, dest: Path) -> Optional[str]:
    """Download from Archive.org"""
    url = f"https://archive.org/download/{archive_id}/{archive_id}_djvu.txt"
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "AstrologIA-KnowledgeBot/1.0"})
        if r.status_code == 200 and len(r.text) > 1000:
            return r.text
    except:
        pass
    # Try alternative
    url2 = f"https://archive.org/stream/{archive_id}/{archive_id}_djvu.txt"
    try:
        r2 = requests.get(url2, timeout=30, headers={"User-Agent": "AstrologIA-KnowledgeBot/1.0"})
        if r2.status_code == 200 and len(r2.text) > 1000:
            return r2.text
    except:
        pass
    return None

def extract_key_passages(text: str, max_chars: int = 50000) -> str:
    """Extract most relevant passages (first 50K chars = ~30 pages)"""
    # Remove Gutenberg header/footer boilerplate
    start_markers = ["*** START OF", "***START OF", "START OF THE PROJECT"]
    end_markers = ["*** END OF", "***END OF", "END OF THE PROJECT"]
    
    for marker in start_markers:
        idx = text.find(marker)
        if idx > 0:
            text = text[idx+len(marker):]
            text = text[text.find('\n')+1:]  # skip rest of marker line
            break
    
    for marker in end_markers:
        idx = text.rfind(marker)
        if idx > 0:
            text = text[:idx]
    
    return text[:max_chars].strip()

def process_book(book: dict) -> dict:
    """Download and process a single book"""
    cat_dir = BASE_DIR / book["cat"]
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{book['id']}_{sanitize_filename(book['title'])}.txt"
    filepath = cat_dir / filename
    
    result = {
        "id": book["id"],
        "title": book["title"],
        "author": book["author"],
        "category": book["cat"],
        "file": str(filepath),
        "status": "pending",
        "size_chars": 0,
        "downloaded_at": None,
    }
    
    # Skip if already downloaded
    if filepath.exists() and filepath.stat().st_size > 1000:
        result["status"] = "already_exists"
        result["size_chars"] = filepath.stat().st_size
        return result
    
    # Try download
    text = None
    if "gutenberg_id" in book:
        text = download_gutenberg(book["gutenberg_id"], cat_dir, book)
    elif "archive_id" in book:
        text = download_archive(book["archive_id"], cat_dir)
    
    if text and len(text) > 500:
        excerpt = extract_key_passages(text)
        
        # Save with metadata header
        header = f"""# {book['title']}
Author: {book['author']}
Category: {book['cat']}
Source: {'Gutenberg #' + str(book.get('gutenberg_id','')) if 'gutenberg_id' in book else 'Archive.org/' + book.get('archive_id','')}
Downloaded: {datetime.now().isoformat()}
AstrologIA Knowledge Base — K2 Sprint
{'='*60}

"""
        filepath.write_text(header + excerpt, encoding='utf-8', errors='replace')
        result["status"] = "downloaded"
        result["size_chars"] = len(excerpt)
        result["downloaded_at"] = datetime.now().isoformat()
    else:
        result["status"] = "failed"
    
    return result

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        SKYNET KNOWLEDGE EXTRACTION — SPRINT K2              ║")
    print(f"║        {len(BOOKS)} libros · 12 categorías · Fuente Primaria            ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    index = {"created": datetime.now().isoformat(), "total": len(BOOKS), "results": []}
    
    stats = {"downloaded": 0, "failed": 0, "exists": 0}
    
    for i, book in enumerate(BOOKS):
        cat_display = book["cat"].split("_",1)[1].upper() if "_" in book["cat"] else book["cat"]
        print(f"  [{i+1:03d}/{len(BOOKS)}] {cat_display} → {book['title'][:50]}")
        
        result = process_book(book)
        index["results"].append(result)
        
        if result["status"] == "downloaded":
            print(f"          ✅ {result['size_chars']:,} chars extraídos")
            stats["downloaded"] += 1
        elif result["status"] == "already_exists":
            print(f"          ⚡ Ya existe ({result['size_chars']:,} bytes)")
            stats["exists"] += 1
        else:
            print(f"          ❌ No disponible online")
            stats["failed"] += 1
        
        # Polite delay
        if "gutenberg_id" in book or "archive_id" in book:
            time.sleep(1.5)
    
    # Save index
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║                SPRINT K2 — RESUMEN FINAL                    ║")
    print(f"║  ✅ Descargados: {stats['downloaded']:3d}                                     ║")
    print(f"║  ⚡ Ya existían: {stats['exists']:3d}                                     ║")
    print(f"║  ❌ No disponibles: {stats['failed']:3d}                                  ║")
    print(f"║  📁 Índice: knowledge/knowledge_index.json                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    main()
