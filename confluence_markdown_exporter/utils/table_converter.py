from bs4 import BeautifulSoup
from bs4 import Comment
from bs4 import NavigableString
from bs4 import Tag
from markdownify import MarkdownConverter
from tabulate import tabulate


def _get_int_attr(cell: Tag, attr: str, default: str = "1") -> int:
    val = cell.get(attr, default)
    if isinstance(val, list):
        val = val[0] if val else default
    try:
        return int(str(val))
    except (ValueError, TypeError):
        return int(default)


def pad(rows: list[list[Tag]]) -> list[list[Tag]]:
    """Pad table rows to handle rowspan and colspan for markdown conversion."""
    padded: list[list[Tag]] = []
    occ: dict[tuple[int, int], Tag] = {}
    for r, row in enumerate(rows):
        if not row:
            continue
        cur: list[Tag] = []
        c = 0
        for cell in row:
            while (r, c) in occ:
                cur.append(occ.pop((r, c)))
                c += 1
            rs = _get_int_attr(cell, "rowspan", "1")
            cs = _get_int_attr(cell, "colspan", "1")
            cur.append(cell)
            # Append extra cells for colspan
            if cs > 1:
                cur.extend(make_empty_cell() for _ in range(1, cs))
            # Mark future cells for rowspan and colspan
            for i in range(rs):
                for j in range(cs):
                    if i or j:
                        occ[(r + i, c + j)] = make_empty_cell()
            c += cs
        while (r, c) in occ:
            cur.append(occ.pop((r, c)))
            c += 1
        padded.append(cur)
    return padded


def make_empty_cell() -> Tag:
    """Return an empty <td> Tag."""
    return Tag(name="td")


def _normalize_table_cell_text(text: str) -> str:
    return (
        text.replace("|", "\\|")  # Escape pipe characters to prevent breaking table formatting
        .replace("{", "\\{")  # Escape curly braces to prevent MDX/JSX expression parsing
        .replace("}", "\\}")
        .replace("\n", "<br/>")  # Replace newlines with <br/> to preserve line breaks in tables
        .removesuffix("<br/>")  # Remove trailing <br/> that may be added by the last cell in a row
        .removeprefix("<br/>")  # Remove leading <br/> that may be added by the first cell in a row
    )


def _collect_direct_rows(table: Tag) -> list[list[Tag]]:
    """Collect only the direct-level <tr> elements of *table*, skipping nested tables."""
    rows: list[list[Tag]] = []
    containers = [
        child
        for child in table.children
        if isinstance(child, Tag) and child.name in ("thead", "tbody", "tfoot")
    ]
    if not containers:
        containers = [table]
    for container in containers:
        for child in container.children:
            if isinstance(child, Tag) and child.name == "tr":
                cells = [c for c in child.children if isinstance(c, Tag) and c.name in ("td", "th")]
                rows.append(cells)
    return rows


class TableConverter(MarkdownConverter):
    """Custom MarkdownConverter for converting HTML tables to markdown tables."""

    def _convert_table_as_html(self, el: BeautifulSoup) -> str:
        """Output the table as raw HTML to preserve nested structure.

        The output is collapsed to a single line so that MDX parsers do not
        split the HTML block at blank lines.  Newlines inside ``<pre>`` are
        kept as ``&#10;`` entities so they still render correctly.  Curly
        braces are escaped as ``&#123;``/``&#125;`` to avoid JSX expression
        parsing.
        """
        soup = BeautifulSoup(str(el), "html.parser")
        for pre in soup.find_all("pre"):
            if pre.string:
                pre.string = pre.string.replace("\n", "&#10;")
        html = str(soup)
        html = html.replace("{", "&#123;").replace("}", "&#125;")
        html = html.replace("\n", " ")
        return f"\n{html}\n"

    _CELL_TEXT_PARENT_TAGS = frozenset({"td", "th", "_inline"})

    def _convert_cell_fragment(self, node: Tag | NavigableString) -> str:
        """Convert one td/th child: nested ``<table>`` subtrees become HTML; else Markdown."""
        if isinstance(node, Comment):
            return ""
        if isinstance(node, NavigableString):
            return self.process_text(node, parent_tags=self._CELL_TEXT_PARENT_TAGS)
        if not isinstance(node, Tag):
            return ""
        if node.name == "table":
            return self._convert_table_as_html(node)
        if not node.find("table"):
            return self.convert(str(node))
        return "".join(self._convert_cell_fragment(c) for c in node.children)

    def _convert_table_cell(self, cell: Tag) -> str:
        """Convert a td/th to Markdown cell text; only nested tables become HTML."""
        if not cell.find("table"):
            return self.convert(str(cell))
        parts = [self._convert_cell_fragment(c) for c in cell.children]
        return _normalize_table_cell_text("".join(parts))

    def convert_table(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        if el.has_attr("style"):
            del el["style"]
        for tag in el.find_all(style=True):
            del tag["style"]

        for a in el.find_all("a", class_="user-mention"):
            a.replace_with(a.get_text())

        rows = _collect_direct_rows(el)

        if not rows:
            return ""

        padded_rows = pad(rows)
        converted = [[self._convert_table_cell(cell) for cell in row] for row in padded_rows]

        has_header = all(cell.name == "th" for cell in rows[0])
        if has_header:
            return tabulate(converted[1:], headers=converted[0], tablefmt="pipe")

        return tabulate(converted, headers=[""] * len(converted[0]), tablefmt="pipe")

    def convert_th(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        """This method is empty because we want a No-Op for the <th> tag."""
        return _normalize_table_cell_text(text)

    def convert_tr(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        """This method is empty because we want a No-Op for the <tr> tag."""
        return text

    def convert_td(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        """This method is empty because we want a No-Op for the <td> tag."""
        return _normalize_table_cell_text(text)

    def convert_thead(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        """This method is empty because we want a No-Op for the <thead> tag."""
        return text

    def convert_tbody(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        """This method is empty because we want a No-Op for the <tbody> tag."""
        return text

    def convert_ol(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        if "td" in parent_tags:
            return str(el)
        return super().convert_ol(el, text, parent_tags)

    def convert_ul(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        if "td" in parent_tags:
            return str(el)
        return super().convert_ul(el, text, parent_tags)

    def convert_p(self, el: BeautifulSoup, text: str, parent_tags: list[str]) -> str:
        md = super().convert_p(el, text, parent_tags)
        if "td" in parent_tags:
            md = md.replace("\n", "") + "<br/>"
        return md
