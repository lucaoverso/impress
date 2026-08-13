import re
import unicodedata


MAX_TAGS_PER_POST = 5
MAX_TAG_LENGTH = 32


def slugify_tag(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:48].rstrip("-")


def normalize_tags(values: list[str] | None) -> list[dict[str, str]]:
    tags: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_value in values or []:
        name = " ".join(str(raw_value or "").strip().lstrip("#").strip().split())
        if not name:
            continue
        if len(name) > MAX_TAG_LENGTH:
            raise ValueError(f"Cada tag deve ter no maximo {MAX_TAG_LENGTH} caracteres.")
        slug = slugify_tag(name)
        if not slug:
            raise ValueError("Use letras ou numeros nas tags.")
        if slug in seen:
            continue
        seen.add(slug)
        tags.append({"name": name, "slug": slug})
    if len(tags) > MAX_TAGS_PER_POST:
        raise ValueError(f"Use no maximo {MAX_TAGS_PER_POST} tags por artigo.")
    return tags
