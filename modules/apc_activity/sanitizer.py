import re
from html import escape
from html.parser import HTMLParser


ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "u", "ol", "ul", "li", "img"}
IMAGE_TOKEN_RE = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png)$")
IMAGE_WIDTHS = {"25", "50", "75", "100"}
IMAGE_ALIGNS = {"left", "center", "right"}
TEXT_ALIGNS = {"left", "center", "right", "justify"}


def _text_alignment(attrs) -> str:
    values = {str(key).lower(): str(value or "").lower() for key, value in attrs}
    direct = values.get("data-align") or values.get("align") or ""
    if direct in TEXT_ALIGNS:
        return direct
    match = re.search(
        r"(?:^|;)\s*text-align\s*:\s*(left|center|right|justify)\s*(?:;|$)",
        values.get("style", ""),
    )
    return match.group(1) if match else "left"


class _ActivityHtmlSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked_depth += 1
            return
        if self.blocked_depth:
            return
        if tag == "div":
            tag = "p"
        if tag not in ALLOWED_TAGS:
            return
        if tag == "img":
            values = {str(key).lower(): str(value or "") for key, value in attrs}
            token = values.get("data-apc-image", "")
            if not IMAGE_TOKEN_RE.fullmatch(token):
                return
            width = values.get("data-width", "50")
            align = values.get("data-align", "center")
            width = width if width in IMAGE_WIDTHS else "50"
            align = align if align in IMAGE_ALIGNS else "center"
            alt = escape(values.get("alt", "Imagem da atividade")[:180], quote=True)
            self.parts.append(
                f'<img data-apc-image="{token}" data-width="{width}" '
                f'data-align="{align}" alt="{alt}">'
            )
            return
        normalized = "strong" if tag == "b" else "em" if tag == "i" else tag
        alignment = _text_alignment(attrs) if normalized in {"p", "li"} else "left"
        attribute = f' data-align="{alignment}"' if alignment != "left" else ""
        self.parts.append(f"<{normalized}{attribute}>")
        if normalized != "br":
            self.stack.append(normalized)

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object"} and self.blocked_depth:
            self.blocked_depth -= 1
            return
        if self.blocked_depth:
            return
        if tag == "div":
            tag = "p"
        normalized = "strong" if tag == "b" else "em" if tag == "i" else tag
        if normalized not in ALLOWED_TAGS or normalized == "br":
            return
        if normalized in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.parts.append(f"</{current}>")
                if current == normalized:
                    break

    def handle_data(self, data: str):
        if self.blocked_depth:
            return
        self.parts.append(escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            self.parts.append(f"</{self.stack.pop()}>")
        return "".join(self.parts).strip()


def sanitize_activity_html(value: str) -> str:
    parser = _ActivityHtmlSanitizer()
    parser.feed(str(value or ""))
    parser.close()
    return parser.result()


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() in {"p", "br", "li"}:
            self.parts.append("\n")
        elif tag.lower() == "img":
            self.parts.append(" [Imagem] ")

    def handle_endtag(self, tag: str):
        if tag.lower() in {"p", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str):
        self.parts.append(data)


def visible_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(str(value or ""))
    return " ".join("".join(parser.parts).split())
