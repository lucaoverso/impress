import html
import re
from html.parser import HTMLParser


_TOKEN_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_CONTAINER_TAGS = {"p", "strong", "b", "em", "i", "u", "ul", "ol", "li", "h2", "figure", "figcaption"}
_ALIGN_PATTERN = re.compile(r"^\s*text-align\s*:\s*(left|center|right)\s*;?\s*$", re.I)
_IMAGE_WIDTHS = {"25", "50", "75", "100"}


class _PublicContentSanitizer(HTMLParser):
    def __init__(self, *, image_base_path: str, images: dict[str, dict]):
        super().__init__(convert_charrefs=True)
        self.image_base_path = image_base_path.rstrip("/")
        self.images = images
        self.parts: list[str] = []
        self.open_tags: list[str] = []
        self.suppressed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.suppressed_depth:
            self.suppressed_depth += 1
            return
        if tag in {"script", "style", "template", "iframe", "object"}:
            self.suppressed_depth = 1
            return
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        if tag == "br":
            self.parts.append("<br>")
            return
        if tag == "img":
            self._append_image(values)
            return
        if tag not in _CONTAINER_TAGS:
            return

        rendered_attrs = ""
        if tag in {"p", "h2", "li"}:
            match = _ALIGN_PATTERN.fullmatch(values.get("style", ""))
            if match:
                rendered_attrs = f' style="text-align: {match.group(1).lower()}"'
        elif tag == "figure":
            token = values.get("data-blog-image", "").lower()
            width = values.get("data-width", "100")
            width = width if width in _IMAGE_WIDTHS else "100"
            rendered_attrs = f' class="blog-article-figure" data-width="{width}"'
            if self._valid_token(token):
                rendered_attrs += f' data-blog-image="{token}"'

        self.parts.append(f"<{tag}{rendered_attrs}>")
        self.open_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self.suppressed_depth:
            self.suppressed_depth -= 1
            return
        tag = tag.lower()
        if tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.parts.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self.suppressed_depth:
            self.parts.append(html.escape(data, quote=False))

    def close(self) -> None:
        super().close()
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")

    def _valid_token(self, token: str) -> bool:
        return bool(_TOKEN_PATTERN.fullmatch(token)) and token in self.images

    def _append_image(self, attrs: dict[str, str]) -> None:
        token = attrs.get("data-blog-image", "").lower()
        if not self._valid_token(token):
            return
        image = self.images[token]
        alt_text = html.escape(str(image.get("alt_text") or ""), quote=True)
        src = html.escape(f"{self.image_base_path}/{token}", quote=True)
        self.parts.append(
            f'<img src="{src}" data-blog-image="{token}" alt="{alt_text}" '
            'loading="lazy" decoding="async">'
        )


def sanitize_public_html(
    value: str, *, image_base_path: str, images: list[dict]
) -> str:
    image_map = {
        str(image.get("token") or "").lower(): image
        for image in images
        if image.get("token")
    }
    parser = _PublicContentSanitizer(
        image_base_path=image_base_path,
        images=image_map,
    )
    parser.feed(str(value or ""))
    parser.close()
    return "".join(parser.parts)
