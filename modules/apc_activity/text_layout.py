import re
from collections.abc import Callable

from .rich_text import Block, Run


def layout_block(
    block: Block,
    width: float,
    measure: Callable[[Run], float],
) -> list[list[Run]]:
    lines: list[list[Run]] = []
    current: list[Run] = []
    current_width = 0.0
    for run in block.runs:
        for token in re.findall(r"\s+|\S+", run.text):
            if token.isspace() and not current:
                continue
            token = " " if token.isspace() else token
            token_run = Run(token, run.bold, run.italic, run.underline)
            token_width = measure(token_run)
            if current and not token.isspace() and current_width + token_width > width:
                while current and current[-1].text.isspace():
                    current_width -= measure(current.pop())
                lines.append(current)
                current, current_width = [token_run], token_width
            else:
                current.append(token_run)
                current_width += token_width
    while current and current[-1].text.isspace():
        current.pop()
    if current:
        lines.append(current)
    return lines or [[]]


def alignment_metrics(
    block: Block,
    line: list[Run],
    line_index: int,
    total_lines: int,
    width: float,
    measure: Callable[[Run], float],
) -> tuple[float, float]:
    line_width = sum(measure(run) for run in line)
    if block.align == "center":
        return max(0.0, (width - line_width) / 2), 0.0
    if block.align == "right":
        return max(0.0, width - line_width), 0.0
    spaces = sum(1 for run in line if run.text.isspace())
    if block.align == "justify" and line_index < total_lines - 1 and spaces:
        return 0.0, max(0.0, width - line_width) / spaces
    return 0.0, 0.0
