"""Unit tests for Confluence Expand → HTML details/summary conversion."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from confluence_markdown_exporter.confluence import Page


def _expand_fixture_html(summary: str, inner_body: str) -> str:
    """Typical Confluence body.view DOM for the Expand macro (expand-container)."""
    return f"""<div class="expand-container conf-macro-output-block">
<div class="expand-control"><span class="expand-control-text">{summary}</span></div>
<div class="expand-content">{inner_body}</div>
</div>"""


class TestExpandConversion:
    """Expand macro maps to Docusaurus-compatible <details>/<summary>."""

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        page = MagicMock(spec=Page)
        page.id = 1
        page.title = "T"
        page.html = "<p>x</p>"
        page.labels = []
        page.ancestors = []
        page.attachments = []
        return page

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_convert_div_routes_expand_container(
        self, mock_settings: MagicMock, mock_page: MagicMock
    ) -> None:
        """document.body.view uses expand-container + expand-control-text + expand-content."""
        mock_settings.export.include_document_title = False
        mock_settings.export.page_breadcrumbs = False

        html = _expand_fixture_html(
            "Toggle me!",
            "<p>Inner <strong>bold</strong>.</p>",
        )
        mock_page.html = html

        md = Page.Converter(mock_page).markdown

        assert "<details>" in md
        assert "<summary>Toggle me!</summary>" in md
        assert "</details>" in md
        assert "Inner" in md
        assert "bold" in md

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_expand_summary_html_escaped(
        self, mock_settings: MagicMock, mock_page: MagicMock
    ) -> None:
        """Characters that break <summary> markup must be escaped."""
        mock_settings.export.include_document_title = False
        mock_settings.export.page_breadcrumbs = False

        bad_summary = 'A < B & C "quoted"'
        html = _expand_fixture_html(bad_summary, "<p>ok</p>")
        mock_page.html = html

        md = Page.Converter(mock_page).markdown

        assert "<summary>A &lt; B &amp; C &quot;quoted&quot;</summary>" in md
        assert "<summary>A < B" not in md

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_convert_expand_container_direct(
        self, mock_settings: MagicMock, mock_page: MagicMock
    ) -> None:
        """convert_expand_container preserves nested structure via process_tag."""
        mock_settings.export.include_document_title = False
        mock_settings.export.page_breadcrumbs = False

        converter = Page.Converter(mock_page)
        inner = """<p>Line one.</p><div class="expand-container conf-macro-output-block">
<div class="expand-control"><span class="expand-control-text">Nested</span></div>
<div class="expand-content"><p>Deep</p></div></div>"""
        el = BeautifulSoup(_expand_fixture_html("Outer", inner), "html.parser").find("div")

        out = converter.convert_expand_container(el, "", [])

        assert out.count("<details>") == 2
        assert "<summary>Nested</summary>" in out
        assert "Deep" in out

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_expand_inside_table_cell_single_line_details(
        self, mock_settings: MagicMock, mock_page: MagicMock
    ) -> None:
        """Table cells normalize newlines to <br/>; details must be one line to stay valid HTML."""
        mock_settings.export.include_document_title = False
        mock_settings.export.page_breadcrumbs = False

        mock_page.html = f"""<table><tbody><tr><td>
{_expand_fixture_html("In cell", "<p>Hidden</p>")}
</td></tr></tbody></table>"""

        md = Page.Converter(mock_page).markdown

        assert "<details><br/>" not in md
        assert "<details><summary>In cell</summary>" in md
        assert "</details>" in md
        assert "Hidden" in md
