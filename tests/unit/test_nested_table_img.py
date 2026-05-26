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
        page.referenced_attachments = []
        page.export_path = Path("/output/SpaceName/sub/page.md")

        att = MagicMock()
        att.export_path = Path("SpaceName/attachments/abc123.png")
        page.get_attachment_by_file_id = MagicMock(return_value=None)
        page.get_attachment_by_id = MagicMock(return_value=att)
        page.get_attachments_by_title = MagicMock(return_value=[])
        page.find_attachment_from_download_url = MagicMock(return_value=att)

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
        page.referenced_attachments = []
        page.export_path = Path("/output/SpaceName/sub/page.md")

        att = MagicMock()
        att.export_path = Path("SpaceName/attachments/abc123.png")
        page.get_attachment_by_file_id = MagicMock(return_value=None)
        page.get_attachment_by_id = MagicMock(return_value=att)
        page.get_attachments_by_title = MagicMock(return_value=[])
        page.find_attachment_from_download_url = MagicMock(return_value=att)

        img_src = "https://example.atlassian.net/wiki/download/attachments/1/x.png"
        page.html = (
            "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td><table>"
            f'<tr><td><img data-linked-resource-id="999" src="{img_src}"/></td></tr>'
            "</table></td></tr></table>"
        )

        md = Page.Converter(page).markdown

        assert "example.atlassian.net" not in md
        assert "SpaceName/attachments/abc123.png" in md.replace("%20", " ")

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_nested_table_img_without_metadata_uses_download_url(
        self, mock_settings: MagicMock
    ) -> None:
        """Cross-page table images often omit ``data-linked-resource-id``; use ``src`` URL."""
        mock_settings.export.attachment_href = "relative"

        page = MagicMock(spec=Page)
        page.id = 6531907886
        page.title = "Guarantee linkage"
        page.base_url = "https://confluence.example.com/confluence"
        page.labels = []
        page.ancestors = []
        page.attachments = []
        page.referenced_attachments = []
        page.export_path = Path("/output/frontend-spec/page.md")

        att = MagicMock()
        att.export_path = Path("attachments/6536868754.png")
        page.get_attachment_by_file_id = MagicMock(return_value=None)
        page.get_attachment_by_id = MagicMock(return_value=None)
        page.get_attachments_by_title = MagicMock(return_value=[])
        page.find_attachment_from_download_url = MagicMock(return_value=att)

        converter = Page.Converter(page)
        src = (
            "https://confluence.example.com/confluence/download/attachments/"
            "6409994109/image-2026-2-26_22-48-33.png?version=1"
        )
        html = (
            "<table><tr><th>Not Found Bank</th><th>Not Found Branch</th></tr>"
            f'<tr><td><img alt="image-2026-2-26_22-48-33.png" src="{src}" width="200"/>'
            "</td><td></td></tr></table>"
        )
        table = BeautifulSoup(html, "html.parser").find("table")
        assert table is not None

        out = converter._convert_table_as_html(table)

        page.find_attachment_from_download_url.assert_called()
        assert "confluence.example.com" not in out
        assert "attachments/6536868754.png" in out.replace("%20", " ")


class TestCrossPageAttachmentExportSelection:
    @patch("confluence_markdown_exporter.confluence.settings")
    def test_attachments_for_export_includes_cross_page_download_url(
        self, mock_settings: MagicMock
    ) -> None:
        mock_settings.export.attachment_export_all = False
        mock_settings.export.include_document_title = False

        foreign = MagicMock()
        foreign.id = "att-foreign"
        foreign.title = "image-2026-2-12_19-26-10.png"
        foreign.filename = "file-id.png"
        foreign.file_id = "file-id"
        foreign.version = MagicMock(number=1)

        page = MagicMock(spec=Page)
        page.id = 6531907886
        page.base_url = "https://confluence.example.com/confluence"
        page.attachments = []
        page.referenced_attachments = []
        page.body = (
            '<p>▼金融機関フォームプロトタイプ</p>'
            '<img src="https://confluence.example.com/confluence/download/attachments/'
            '6409994109/image-2026-2-12_19-26-10.png?version=1" />'
        )
        page.body_export = ""
        page.title = "Guarantee linkage"
        page._attachment_reference_html = Page._attachment_reference_html.__get__(page, Page)
        page.find_attachment_by_container_and_filename = (
            Page.find_attachment_by_container_and_filename.__get__(page, Page)
        )
        fetch_mock = MagicMock(return_value=(foreign,))
        page._fetch_attachments_for_page = fetch_mock

        selected = Page._attachments_for_export(page)

        fetch_mock.assert_called_with("https://confluence.example.com/confluence", 6409994109)
        assert selected == [foreign]

