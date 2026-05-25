import re
import time
import unicodedata
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}


def get_raw_data(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text


def sanitize_text(text: str) -> str:
    if not text:
        return None
    s = re.sub(r"[\r\t]", "", text)
    s = re.sub(r"\n+", "\n", s)
    s = re.sub(r"[ ]{2,}", " ", s)
    return s.strip()


def same_domain(url, base):
    try:
        def normalize(netloc):
            return re.sub(r"^www\d*\.", "", netloc.lower())

        return normalize(urlparse(url).netloc) == normalize(urlparse(base).netloc)
    except Exception:
        return False


def collect_links_from_home(base_url):
    raw = get_raw_data(base_url)
    soup = BeautifulSoup(raw, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        if same_domain(full, base_url):
            links.add(full)
    return list(links)


def collect_candidates_from_home(base_url):
    raw = get_raw_data(base_url)
    soup = BeautifulSoup(raw, "html.parser")
    candidates = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        if not same_domain(full, base_url) or full in seen:
            continue
        seen.add(full)
        title = sanitize_text(a.get_text(" ", strip=True))
        if title:
            candidates.append({"url": full, "title": title, "resume": None, "source_page": base_url})
    return candidates


def discover_city_sections(base_url):
    raw = get_raw_data(base_url)
    soup = BeautifulSoup(raw, "html.parser")
    sections = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a.get("href"))
        if not same_domain(href, base_url):
            continue
        path = urlparse(href).path.lower()
        if any(token in path for token in ("sao-paulo", "são-paulo", "rio-de-janeiro", "/sp/", "/rj/")):
            if not any(token in path for token in ("/noticia/", ".shtml", ".ghtml")):
                sections.add(href)
    return list(sections)


def collect_links_from_feeds(base_url, pages=3):
    links = set()
    for p in range(1, pages + 1):
        feed_url = base_url.rstrip('/') + f'/index/feed/pagina-{p}.ghtml'
        try:
            raw = get_raw_data(feed_url)
        except Exception:
            continue
        soup = BeautifulSoup(raw, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get('href')
            if not href:
                continue
            full = urljoin(base_url, href)
            if same_domain(full, base_url) and url_path_filter(full):
                links.add(full)
    return list(links)


def collect_candidates_from_feeds(base_url, pages=3):
    candidates = []
    seen = set()
    for p in range(1, pages + 1):
        feed_url = base_url.rstrip('/') + f'/index/feed/pagina-{p}.ghtml'
        try:
            raw = get_raw_data(feed_url)
        except Exception:
            continue
        soup = BeautifulSoup(raw, "html.parser")
        for el in soup.find_all(class_=re.compile("feed-post-link", re.I)):
            href = ""
            if el.name == "a" and el.get("href"):
                href = urljoin(base_url, el.get("href"))
            else:
                a = el.find("a", href=True) or el.find_parent("a", href=True)
                if a:
                    href = urljoin(base_url, a.get("href"))
            if not href or href in seen or not same_domain(href, base_url):
                continue
            seen.add(href)
            title = sanitize_text(el.get_text(" ", strip=True))
            resume_tag = None
            parent = el.parent
            if parent:
                resume_tag = parent.find(class_=re.compile("feed-post-body-resumo", re.I))
                if not resume_tag:
                    for sib in parent.next_siblings:
                        if hasattr(sib, "find"):
                            resume_tag = sib.find(class_=re.compile("feed-post-body-resumo", re.I))
                            if resume_tag:
                                break
            resume = sanitize_text(resume_tag.get_text(" ", strip=True)) if resume_tag else None
            if title:
                candidates.append({"url": href, "title": title, "resume": resume, "source_page": feed_url})
    return candidates


def get_feed_news(base_url, pages=1):
    results = []
    for p in range(1, pages + 1):
        feed_url = base_url.rstrip('/') + f'/index/feed/pagina-{p}.ghtml'
        try:
            raw = get_raw_data(feed_url)
        except Exception:
            continue
        soup = BeautifulSoup(raw, "html.parser")
        elems = soup.find_all(class_=re.compile("feed-post-link", re.I))
        for el in elems:
            # get link
            href = ""
            if el.name == "a" and el.get("href"):
                href = urljoin(base_url, el.get("href"))
            else:
                a = el.find("a", href=True) or el.find_parent("a", href=True)
                if a:
                    href = urljoin(base_url, a.get("href"))

            title = sanitize_text(el.get_text()) or None

            # try to find resume near the element
            resume_tag = None
            parent = el.parent
            if parent:
                resume_tag = parent.find(class_=re.compile("feed-post-body-resumo", re.I))
                if not resume_tag:
                    # search siblings
                    for sib in parent.next_siblings:
                        if hasattr(sib, "find"):
                            resume_tag = sib.find(class_=re.compile("feed-post-body-resumo", re.I))
                            if resume_tag:
                                break
            resume = sanitize_text(resume_tag.get_text()) if resume_tag else None

            results.append({"title": title, "resume": resume, "link": href})
    return results


INCLUDE_PATHS = (
    "/cotidiano/",
    "/seguranca/",
    "/noticia/",
    "/mundo/",
    "/brasil/",
    # common patterns for UOL/Folha and other portals
    "/noticias/",
    "/ultimas",
    "/ultimas-noticias",
)
INCLUDE_KEYWORDS = [
    "furto",
    "roubo",
    "assalto",
    "acidente",
    "colisão",
    "colisao",
    "atropelamento",
    "trânsito",
    "transito",
    "vandalismo",
    "invasão",
    "invasao",
    "estupro",
    "violência sexual",
    "violencia sexual",
    "abuso sexual",
    "exploração sexual",
    "exploracao sexual",
    "homicídio",
    "homicidio",
    "feminicídio",
    "feminicidio",
    "sequestro",
    "tiroteio",
    "tráfico",
    "trafico",
]
CITY_KEYWORDS = [
    "são paulo",
    "sao paulo",
    "rio de janeiro",
    "rj",
    "sp",
]
EXCLUDE_KEYWORDS = ["opinião", "opinia", "coluna", "patrocinado", "esportes", "futebol"]

SAO_PAULO_NEIGHBORHOODS = [
    "Aclimacao",
    "Alto de Pinheiros",
    "Barra Funda",
    "Bela Vista",
    "Belém",
    "Bom Retiro",
    "Brás",
    "Brooklin",
    "Butantã",
    "Campo Belo",
    "Campo Grande",
    "Campo Limpo",
    "Carrão",
    "Casa Verde",
    "Cidade Ademar",
    "Cidade Dutra",
    "Cidade Jardim",
    "Cidade Líder",
    "Consolação",
    "Cursino",
    "Ermelino Matarazzo",
    "Freguesia do Ó",
    "Grajaú",
    "Ipiranga",
    "Itaim Bibi",
    "Itaim Paulista",
    "Itaquera",
    "Jabaquara",
    "Jaçanã",
    "Jaguara",
    "Jaguaré",
    "Jardim América",
    "Jardim Ângela",
    "Jardim Europa",
    "Jardim Helena",
    "Jardim Paulista",
    "Jardim São Luís",
    "Jardins",
    "Lapa",
    "Liberdade",
    "Limão",
    "Mandaqui",
    "Moema",
    "Mooca",
    "Morumbi",
    "Parelheiros",
    "Pari",
    "Penha",
    "Perdizes",
    "Perus",
    "Pinheiros",
    "Pirituba",
    "República",
    "Rio Pequeno",
    "Sacomã",
    "Santa Cecília",
    "Santana",
    "Santo Amaro",
    "Sapopemba",
    "Saúde",
    "Sé",
    "Socorro",
    "Tatuapé",
    "Tremembé",
    "Tucuruvi",
    "Vila Andrade",
    "Vila Clementino",
    "Vila Formosa",
    "Vila Leopoldina",
    "Vila Madalena",
    "Vila Mariana",
    "Vila Matilde",
    "Vila Prudente",
]

RIO_DE_JANEIRO_NEIGHBORHOODS = [
    "Anil",
    "Bangu",
    "Barra da Tijuca",
    "Benfica",
    "Bento Ribeiro",
    "Bonsucesso",
    "Botafogo",
    "Brás de Pina",
    "Cachambi",
    "Caju",
    "Camorim",
    "Campo Grande",
    "Catete",
    "Catumbi",
    "Centro",
    "Cidade de Deus",
    "Cidade Nova",
    "Cocotá",
    "Copacabana",
    "Cordovil",
    "Cosme Velho",
    "Del Castilho",
    "Engenho de Dentro",
    "Engenho Novo",
    "Estácio",
    "Flamengo",
    "Freguesia",
    "Gamboa",
    "Glória",
    "Grajaú",
    "Guaratiba",
    "Humaitá",
    "Ilha do Governador",
    "Inhaúma",
    "Ipanema",
    "Irajá",
    "Jacarepaguá",
    "Jardim Botânico",
    "Lagoa",
    "Laranjeiras",
    "Leblon",
    "Leme",
    "Madureira",
    "Mangueira",
    "Maracanã",
    "Méier",
    "Marechal Hermes",
    "Olaria",
    "Paciência",
    "Padre Miguel",
    "Pavuna",
    "Penha",
    "Penha Circular",
    "Pechincha",
    "Piedade",
    "Praça Seca",
    "Quintino Bocaiúva",
    "Ramos",
    "Realengo",
    "Recreio dos Bandeirantes",
    "Rio Comprido",
    "Rocha",
    "Rocha Miranda",
    "Santa Cruz",
    "Santa Teresa",
    "São Conrado",
    "São Cristóvão",
    "Taquara",
    "Tijuca",
    "Todos os Santos",
    "Urca",
    "Vargem Grande",
    "Vargem Pequena",
    "Vaz Lobo",
    "Vila Isabel",
]


def normalize_for_lookup(text: str):
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", " ", norm)
    return re.sub(r"\s{2,}", " ", norm).strip()


def build_neighborhood_index():
    entries = {}
    for bairro in SAO_PAULO_NEIGHBORHOODS:
        key = normalize_for_lookup(bairro)
        entries.setdefault(key, []).append({"bairro": bairro, "cidade": "São Paulo"})
    for bairro in RIO_DE_JANEIRO_NEIGHBORHOODS:
        key = normalize_for_lookup(bairro)
        entries.setdefault(key, []).append({"bairro": bairro, "cidade": "Rio de Janeiro"})
    return entries


NEIGHBORHOOD_INDEX = build_neighborhood_index()
NEIGHBORHOOD_KEYS = sorted(NEIGHBORHOOD_INDEX.keys(), key=len, reverse=True)

NEIGHBORHOOD_PATTERNS = [
    re.compile(
        r"\bbairro\s+(?:do|da|de)?\s*([A-Za-zÀ-ÿ0-9'’\-]+(?:\s+[A-Za-zÀ-ÿ0-9'’\-]+){0,4})",
        re.I,
    ),
    re.compile(
        r"\bno\s+bairro\s+(?:do|da|de)?\s*([A-Za-zÀ-ÿ0-9'’\-]+(?:\s+[A-Za-zÀ-ÿ0-9'’\-]+){0,4})",
        re.I,
    ),
]


def url_path_filter(href: str) -> bool:
    return any(p in href for p in INCLUDE_PATHS) and not any(x in href for x in ("/esporte", "/futebol", "/basquete", "/olimpiadas", "/formula-1", "/motor"))


def title_filters(title: str) -> bool:
    if not title:
        return False
    t = title.lower()
    if any(ex in t for ex in EXCLUDE_KEYWORDS):
        return False
    return any(inc in t for inc in INCLUDE_KEYWORDS)


def city_filters(candidate):
    title = (candidate.get("title") or "").lower()
    resume = (candidate.get("resume") or "").lower()
    url = (candidate.get("url") or "").lower()
    path = urlparse(url).path.lower()

    text = f"{title} {resume} {path}"

    if any(city in text for city in ("são paulo", "sao paulo", "rio de janeiro")):
        return True

    # fallback for site paths that explicitly encode the city/state section
    return any(segment in path for segment in ("/sao-paulo/", "/rio-de-janeiro/", "/sp/", "/rj/"))


def detect_city(candidate):
    text = " ".join(
        [
            candidate.get("title") or "",
            candidate.get("resume") or "",
            candidate.get("url") or "",
        ]
    ).lower()
    path = urlparse(candidate.get("url") or "").path.lower()
    if any(token in text or token in path for token in ("são paulo", "sao paulo", "/sp/")):
        return "São Paulo"
    if any(token in text or token in path for token in ("rio de janeiro", "/rj/", "/rio-de-janeiro/")):
        return "Rio de Janeiro"
    return None


def normalize_neighborhood(name: str):
    if not name:
        return None
    cleaned = sanitize_text(name)
    if not cleaned:
        return None
    cleaned = re.sub(r"^[\-,:;\s]+|[\-,:;\s]+$", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    if not cleaned:
        return None
    return cleaned.title()


def extract_neighborhood_from_text(text: str):
    if not text:
        return None
    for pattern in NEIGHBORHOOD_PATTERNS:
        match = pattern.search(text)
        if match:
            return normalize_neighborhood(match.group(1))
    return None


def extract_neighborhood_from_list(text: str, city_hint: str = None):
    norm = normalize_for_lookup(text)
    if not norm:
        return None, None

    for key in NEIGHBORHOOD_KEYS:
        if not re.search(rf"\b{re.escape(key)}\b", norm):
            continue
        entries = NEIGHBORHOOD_INDEX[key]
        if city_hint:
            for entry in entries:
                if entry["cidade"] == city_hint:
                    return entry["bairro"], entry["cidade"]
            continue
        # when the same neighborhood exists in more than one city and we have no
        # city hint, keep it unresolved to avoid assigning the wrong city.
        if len(entries) > 1:
            return entries[0]["bairro"], None
        return entries[0]["bairro"], entries[0]["cidade"]

    return None, None


def detect_neighborhood(candidate, article_data=None):
    # prefer article body/title/subtitle first, then fallback to candidate/url text
    sources = []
    if article_data:
        sources.extend(
            [
                article_data.get("titulo") or "",
                article_data.get("subtitulo") or "",
                article_data.get("corpo_texto") or "",
                article_data.get("url_origem") or "",
            ]
        )
    sources.extend(
        [
            candidate.get("title") or "",
            candidate.get("resume") or "",
            candidate.get("url") or "",
        ]
    )

    for source in sources:
        bairro = extract_neighborhood_from_text(source)
        if bairro:
            return bairro, None

    city_hint = (
        detect_city(candidate)
        or detect_city(
            {
                "title": (article_data or {}).get("titulo"),
                "resume": (article_data or {}).get("subtitulo"),
                "url": (article_data or {}).get("url_origem"),
            }
        )
    )

    for source in sources:
        bairro, cidade = extract_neighborhood_from_list(source, city_hint=city_hint)
        if bairro:
            return bairro, cidade

    return None, None


def candidate_matches_crime(candidate):
    title = (candidate.get("title") or "").lower()
    resume = (candidate.get("resume") or "").lower()
    url = (candidate.get("url") or "").lower()
    if any(ex in title for ex in EXCLUDE_KEYWORDS):
        return False, None
    # allow URLs outside the standard include paths if the text explicitly
    # contains one of the include keywords (covers sections like /carros/ or /tilt/)
    if not url_path_filter(url):
        text = f"{title} {resume} {url}"
        if not any(inc in text for inc in INCLUDE_KEYWORDS):
            return False, None
    # don't require explicit city info at this stage; allow candidates even when
    # city is not present in title/resume/url so broader sites (UOL/Folha) yield results
    # city check is applied later when extracting the full article (but we also
    # accept articles without a detected city)
    text = f"{title} {resume} {url}"
    for inc in INCLUDE_KEYWORDS:
        if inc in text:
            return True, inc
    return False, None


def extract_article_fields(url):
    try:
        raw = get_raw_data(url)
    except Exception:
        return None
    soup = BeautifulSoup(raw, "html.parser")

    # remove unwanted sections
    for tag in soup(["aside", "footer", "script", "style", "iframe"]):
        tag.decompose()

    # title
    h1 = soup.find("h1")
    titulo = sanitize_text(h1.get_text()) if h1 else None

    # subtitle (often h2 or summary)
    h2 = soup.find("h2")
    subtitulo = sanitize_text(h2.get_text()) if h2 else None

    # published date
    data_publicacao = None
    time_tag = soup.find("time")
    if time_tag:
        dt = time_tag.get("datetime") or time_tag.get_text()
        try:
            parsed = dateparser.parse(dt)
            if parsed:
                data_publicacao = parsed.date().isoformat()
        except Exception:
            data_publicacao = None

    # author
    autor = None
    author_tag = soup.find(attrs={"rel": "author"}) or soup.find(class_=re.compile("author|autor", re.I))
    if author_tag:
        autor = sanitize_text(author_tag.get_text())
        if autor:
            autor = re.sub(r'^(Por|Escrito por)\s*', "", autor, flags=re.I).strip()

    # body text: prefer <article>, else a main content container
    body_text = []
    article = soup.find("article")
    container = article or soup.find(class_=re.compile("content|materia|article|post|texto", re.I)) or soup.find("main")
    if container:
        for p in container.find_all("p"):
            text = p.get_text(separator=" ")
            if not text:
                continue
            low = text.lower()
            if "leia também" in low or "leia tamb" in low:
                continue
            # skip paragraphs that are mostly links/ads
            if p.find("a") and len(text.strip()) < 40:
                continue
            body_text.append(sanitize_text(text))
    corpo_texto = "\n\n".join([t for t in body_text if t]) or None

    return {
        "titulo": titulo,
        "subtitulo": subtitulo,
        "data_publicacao": data_publicacao,
        "autor": autor,
        "corpo_texto": corpo_texto,
        "url_origem": url,
    }


def scrape_security_articles(base_url, max_articles=100, delay=2, pages_feed=4, require_neighborhood=False):
    # collect titles/resumes first, then fetch full article only when the candidate matches
    candidates = collect_candidates_from_feeds(base_url, pages=pages_feed)
    candidates.extend(collect_candidates_from_home(base_url))
    for section_url in discover_city_sections(base_url):
        candidates.extend(collect_candidates_from_home(section_url))
    results = []
    seen = set()
    for candidate in candidates:
        if len(results) >= max_articles:
            break
        href = candidate.get("url")
        if not href or href in seen:
            continue
        seen.add(href)
        matched, matched_term = candidate_matches_crime(candidate)
        if not matched:
            continue

        # passed filters — extract full article
        data = extract_article_fields(href)
        if data:
            bairro, cidade_bairro = detect_neighborhood(candidate, data)
            if require_neighborhood and not bairro:
                continue

            data["pagina_obtida"] = href
            data["pagina_coleta"] = candidate.get("source_page")
            data["termo_encontrado"] = matched_term
            data["cidade_encontrada"] = (
                detect_city(candidate)
                or detect_city({"title": data.get("titulo"), "resume": data.get("subtitulo"), "url": href})
                or cidade_bairro
                or None
            )
            data["bairro_encontrado"] = bairro
            results.append(data)

        time.sleep(delay)

    return results

