from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class Block:
    runs: list[Run]
    marker: str = ""
    indent: int = 0
    align: str = "left"


@dataclass
class ImageBlock:
    token: str
    width_percent: int = 50
    align: str = "center"
    alt: str = ""


class _RichParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block | ImageBlock] = []
        self.runs: list[Run] = []
        self.bold = False
        self.italic = False
        self.underline = False
        self.lists: list[tuple[str, int]] = []
        self.list_counts: list[int] = []
        self.pending_marker = ""
        self.alignment = "left"

    def _flush(self):
        if self.runs or self.pending_marker:
            self.blocks.append(
                Block(
                    self.runs,
                    self.pending_marker,
                    max(0, len(self.lists) - 1),
                    self.alignment,
                )
            )
        self.runs = []
        self.pending_marker = ""

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        if tag == "img":
            self._flush()
            token = values.get("data-apc-image", "")
            width = values.get("data-width", "50")
            self.blocks.append(
                ImageBlock(
                    token=token,
                    width_percent=int(width) if width.isdigit() else 50,
                    align=values.get("data-align", "center"),
                    alt=values.get("alt", ""),
                )
            )
        elif tag == "p":
            self._flush()
            self.alignment = values.get("data-align", "left")
        elif tag == "strong":
            self.bold = True
        elif tag == "em":
            self.italic = True
        elif tag == "u":
            self.underline = True
        elif tag == "br":
            self._flush()
        elif tag in {"ol", "ul"}:
            self.lists.append((tag, 0))
            self.list_counts.append(0)
        elif tag == "li":
            self._flush()
            self.alignment = values.get("data-align", "left")
            if self.lists:
                list_type, _ = self.lists[-1]
                self.list_counts[-1] += 1
                number = self.list_counts[-1]
                if list_type == "ol":
                    self.pending_marker = f"{number}." if len(self.lists) == 1 else f"{chr(64 + min(number, 26))})"
                else:
                    self.pending_marker = "•"

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag == "strong":
            self.bold = False
        elif tag == "em":
            self.italic = False
        elif tag == "u":
            self.underline = False
        elif tag in {"p", "li"}:
            self._flush()
            self.alignment = "left"
        elif tag in {"ol", "ul"} and self.lists:
            self.lists.pop()
            self.list_counts.pop()

    def handle_data(self, data: str):
        if data:
            self.runs.append(Run(data, self.bold, self.italic, self.underline))

    def result(self) -> list[Block | ImageBlock]:
        self._flush()
        return self.blocks


def parse_html(value: str) -> list[Block | ImageBlock]:
    parser = _RichParser()
    parser.feed(str(value or ""))
    parser.close()
    return parser.result()
