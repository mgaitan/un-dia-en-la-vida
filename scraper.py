# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "bs4",
#   "rich",
#   "requests",
# ]
# ///

from __future__ import annotations

import json
import re
from argparse import ArgumentParser, Namespace
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from rich.console import Console
from rich.progress import track

console = Console()

BASE_LISTING = "https://cenital.com/secciones/newsletters/un-dia-en-la-vida/"
OUTPUT_DIR = Path("entregas")

EXTRA_URLS = [
    "https://cenital.com/un-equipo-que-hizo-politica-la-democracia-corinthiana/",
]

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass
class Article:
    url: str
    title: str
    subtitle: str
    date_iso: str
    featured_image: Optional[str]
    content_blocks: list[str]
    slug: str


def fetch(url: str, *, allow_404: bool = False) -> Optional[str]:
    resp = requests.get(url, timeout=20)
    if resp.status_code == 404 and allow_404:
        return None
    resp.raise_for_status()
    return resp.text


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def parse_date(text: str) -> str:
    m = re.search(
        r"(?P<day>\d{1,2})\s+de\s+(?P<month>[A-Za-záéíóúñ]+)"
        r"(?:\s*(?:,|de)\s*)?(?P<year>\d{4})",
        text.lower(),
    )
    if not m:
        raise ValueError(f"No pude parsear la fecha: {text!r}")
    day = int(m.group("day"))
    month_name = m.group("month")
    if month_name not in MONTHS:
        raise ValueError(f"Mes desconocido: {month_name}")
    month = MONTHS[month_name]
    year = int(m.group("year"))
    return f"{year:04d}-{month:02d}-{day:02d}"


def format_pretty_date(date_iso: str) -> str:
    """Render a human-friendly publication date."""
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    month_name = [
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ][dt.month].capitalize()
    return f"Publicado el {dt.day} de {month_name} de {dt.year}"


def slugify(text: str) -> str:
    text = normalize_spaces(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúñü-]+", "-", text)
    text = text.strip("-")
    return text or "articulo"


def clean_image_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("data:"):
        return None
    cleaned = url.split("?", 1)[0]
    if "smush-webp" in cleaned and cleaned.endswith(".webp"):
        cleaned = cleaned.replace("/smush-webp/", "/uploads/")
        cleaned = cleaned[:-5]
    elif cleaned.endswith(".webp"):
        # No formato aceptado por EPUB, preferimos omitir
        return None
    if cleaned.endswith(".avif"):
        return None
    return cleaned


def extract_img_src(img: Tag) -> Optional[str]:
    """Return the best image URL from the various lazy-loading attributes."""

    def first_from_srcset(srcset: str) -> str:
        # Each entry looks like "url width". We only care about the first URL.
        return srcset.split(",")[0].strip().split()[0]

    candidates = []
    data_src = img.get("data-src")
    if data_src:
        candidates.append(data_src)
    for attr in ("data-srcset", "srcset"):
        srcset = img.get(attr)
        if srcset:
            candidates.append(first_from_srcset(srcset))
    src = img.get("src")
    if src:
        candidates.append(src)
    fallback = img.get("data-smush-webp-fallback")
    if fallback:
        try:
            fallback_data = json.loads(fallback)
            fallback_src = fallback_data.get("src")
            if fallback_src:
                candidates.append(fallback_src)
        except json.JSONDecodeError:
            pass
    for candidate in candidates:
        cleaned = clean_image_url(candidate)
        if cleaned:
            return cleaned
    return None


def text_with_links(tag: Tag) -> str:
    """Convert a paragraph tag into Markdown, preserving links."""
    parts: list[str] = []
    for child in tag.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
            continue
        if isinstance(child, Tag):
            if child.name == "a":
                href = child.get("href")
                text = child.get_text(" ", strip=True)
                if href and text:
                    parts.append(f"[{text}]({href})")
                    continue
                if text:
                    parts.append(text)
                    continue
            text = child.get_text(" ", strip=True)
            if text:
                parts.append(text)
    return normalize_spaces(" ".join(parts))


def iter_listing_pages(max_pages: Optional[int] = None) -> Iterator[str]:
    # Yield known extras first to avoid missing featured/spotlight articles.
    for extra in EXTRA_URLS:
        yield extra

    page = 1
    while True:
        if max_pages and page > max_pages:
            break
        url = BASE_LISTING if page == 1 else f"{BASE_LISTING}page/{page}/"
        html = fetch(url, allow_404=True)
        if html is None:
            break
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.post a.post__image[href]")
        if not articles:
            break
        for a in articles:
            yield a["href"]
        page += 1


def extract_article(url: str) -> Article:
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("h1.title")
    subtitle_tag = soup.select_one("p.subtitle")
    date_tag = soup.select_one("div.byline__date")

    if not title_tag or not subtitle_tag or not date_tag:
        raise ValueError(f"Faltan campos obligatorios en {url}")

    title = normalize_spaces(title_tag.get_text())
    subtitle = normalize_spaces(subtitle_tag.get_text())
    date_iso = parse_date(date_tag.get_text())

    img_tag = soup.select_one("img.single__featured-image")
    featured_image = None
    if img_tag:
        featured_image = extract_img_src(img_tag)

    main = soup.find("main")
    if not isinstance(main, Tag):
        raise ValueError(f"No encontré <main> en {url}")

    content_blocks: list[str] = []
    for node in main.children:
        if isinstance(node, str):
            continue
        if isinstance(node, Tag):
            if node.name in {"h2", "h3"}:
                heading_text = normalize_spaces(node.get_text())
                if heading_text.lower().strip(":") == "otras lecturas":
                    break
                if heading_text:
                    content_blocks.append(f"## {heading_text}")
                continue
            if "contextual_box" in node.get("class", []):
                continue
            if "single-post-box" in node.get("class", []) or "subscription" in node.get(
                "class", []
            ):
                continue
            if node.name == "p":
                txt = text_with_links(node)
                if txt:
                    content_blocks.append(txt)
                continue
            if node.name == "figure":
                img = node.find("img")
                if img:
                    src = extract_img_src(img)
                    alt = normalize_spaces(img.get("alt", ""))
                    if src:
                        content_blocks.append(f"![{alt}]({src})")
                continue
            if node.name == "div" and "wp-block-image" in node.get("class", []):
                img = node.find("img")
                if img:
                    src = extract_img_src(img)
                    alt = normalize_spaces(img.get("alt", ""))
                    if src:
                        content_blocks.append(f"![{alt}]({src})")
                continue
    slug = slugify(title)
    return Article(
        url=url,
        title=title,
        subtitle=subtitle,
        date_iso=date_iso,
        featured_image=featured_image,
        content_blocks=content_blocks,
        slug=slug,
    )


def render_article_md(article: Article) -> str:
    parts = [
        f"# {article.title}",
        "",
        f"*{article.subtitle}*",
        "",
        f"**{format_pretty_date(article.date_iso)}**",
    ]
    if article.featured_image:
        parts.extend(["", f"![Portada]({article.featured_image})", ""])
    else:
        parts.append("")
    for block in article.content_blocks:
        parts.append(block)
        parts.append("")
    parts.extend(
        [
            "<hr />",
            "",
            f"[URL original]({article.url})",
        ]
    )
    return "\n".join(parts)


def write_articles(articles: Iterable[Article]) -> list[Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = []
    for article in articles:
        filename = f"{article.date_iso}-{article.slug}.md"
        path = OUTPUT_DIR / filename
        path.write_text(render_article_md(article), encoding="utf-8")
        written.append(path)
    return written


def update_index(entries: list[Path]) -> None:
    entries_sorted = sorted(entries, key=lambda p: p.name)
    static_entries = ["AGENTS.md"]
    lines = Path("index.md").read_text(encoding="utf-8").splitlines()
    new_lines = []
    in_toctree = False
    inserted = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```{toctree}"):
            in_toctree = True
            new_lines.append("```{toctree}")
            new_lines.append(":maxdepth: 2")
            new_lines.append(":caption: Documentation")
            new_lines.append("")
            continue
        if in_toctree and stripped.startswith("```"):
            insert_block = [entry for entry in static_entries]
            insert_block += [p.as_posix() for p in entries_sorted]
            new_lines.extend(insert_block)
            new_lines.append(line)
            in_toctree = False
            inserted = True
            continue
        if in_toctree:
            # Skip existing entries inside toctree block
            continue
        if stripped.startswith("entregas/"):
            # Limpia restos de inserciones previas fuera del bloque
            continue
        new_lines.append(line)
    if not inserted:
        insert_block = [entry for entry in static_entries]
        insert_block += [p.as_posix() for p in entries_sorted]
        new_lines.extend(
            [
                "```{toctree}",
                ":maxdepth: 2",
                ":caption: Documentation",
                "",
                *insert_block,
                "```",
            ]
        )
    Path("index.md").write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Descarga y formatea los artículos del newsletter.")
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Cantidad de páginas de listado a scrapear (por defecto todas hasta 404).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Máximo de artículos a descargar (útil para pruebas rápidas).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    console.print("[bold]Obteniendo listado de artículos...[/bold]")
    links = list(dict.fromkeys(iter_listing_pages(args.pages)))
    if args.limit:
        links = links[: args.limit]
    console.print(f"Encontrados {len(links)} links.")

    articles = []
    for link in track(links, description="Descargando artículos"):
        try:
            articles.append(extract_article(link))
        except Exception as exc:  # pragma: no cover - logging
            console.print(f"[red]Error con {link}: {exc}[/red]")
            raise

    console.print("Escribiendo archivos markdown...")
    written = write_articles(articles)
    console.print(f"Generados {len(written)} archivos en {OUTPUT_DIR}/")
    console.print("Actualizando index.md...")
    update_index(written)
    console.print("[green]Listo.[/green]")


if __name__ == "__main__":
    main()
