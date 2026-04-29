"""Nested HTML tables: embedded ``<img>`` src should point at exported attachment paths."""

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from bs4 import BeautifulSoup

from confluence_markdown_exporter.confluence import Page


class TestNestedTableImgSrc:
    @patch("confluence_markdown_exporter.confluence.settings")
    def test_nested_table_img_rewrites_src_to_attachment_path(
        self, mock_settings: MagicMock
    ) -> None:
        mock_settings.export.attachment_href = "relative"

        page = MagicMock(spec=Page)
        page.id = 1
        page.title = "Page"
        page.base_url = "https://example.atlassian.net/wiki"
        page.html = "<p>x</p>"
        page.labels = []
        page.ancestors = []
        page.attachments = []
        page.export_path = Path("/output/SpaceName/sub/page.md")

        att = MagicMock()
        att.export_path = Path("SpaceName/attachments/abc123.png")
        page.get_attachment_by_file_id = MagicMock(return_value=None)
        page.get_attachment_by_id = MagicMock(return_value=att)
        page.get_attachments_by_title = MagicMock(return_value=[])

        converter = Page.Converter(page)
        src = "https://example.atlassian.net/wiki/download/attachments/1/x.png"
        html = (
            f'<table><tr><td><img data-linked-resource-id="999" src="{src}" '
            f'alt="x"/></td></tr></table>'
        )
        table = BeautifulSoup(html, "html.parser").find("table")
        assert table is not None

        out = converter._convert_table_as_html(table)

        assert "example.atlassian.net" not in out
        assert "SpaceName/attachments/abc123.png" in out.replace("%20", " ")

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_nested_table_in_markdown_cell_with_img(
        self, mock_settings: MagicMock
    ) -> None:
        mock_settings.export.include_document_title = False
        mock_settings.export.page_breadcrumbs = False
        mock_settings.export.attachment_href = "relative"

        page = MagicMock(spec=Page)
        page.id = 1
        page.title = "Page"
        page.base_url = "https://example.atlassian.net/wiki"
        page.labels = []
        page.ancestors = []
        page.attachments = []
        page.export_path = Path("/output/SpaceName/sub/page.md")

        att = MagicMock()
        att.export_path = Path("SpaceName/attachments/abc123.png")
        page.get_attachment_by_file_id = MagicMock(return_value=None)
        page.get_attachment_by_id = MagicMock(return_value=att)
        page.get_attachments_by_title = MagicMock(return_value=[])

        img_src = "https://example.atlassian.net/wiki/download/attachments/1/x.png"
        page.html = (
            "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td><table>"
            f'<tr><td><img data-linked-resource-id="999" src="{img_src}"/></td></tr>'
            "</table></td></tr></table>"
        )

        md = Page.Converter(page).markdown

        assert "example.atlassian.net" not in md
        assert "SpaceName/attachments/abc123.png" in md.replace("%20", " ")
