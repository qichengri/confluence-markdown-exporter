"""Tests for the table_converter module."""

from bs4 import BeautifulSoup

from confluence_markdown_exporter.utils.table_converter import TableConverter


class TestTableConverter:
    """Test TableConverter class."""

    def test_pipe_character_in_cell(self) -> None:
        """Test that pipe characters are escaped in table cells."""
        html = """
        <table>
            <tr>
                <th>Column 1</th>
                <th>Column 2</th>
            </tr>
            <tr>
                <td>Value with | pipe</td>
                <td>Normal value</td>
            </tr>
        </table>
        """
        BeautifulSoup(html, "html.parser")
        converter = TableConverter()
        result = converter.convert(html)

        # The pipe character should be escaped
        assert "\\|" in result
        # The result should still have proper table structure
        assert "Column 1" in result
        assert "Column 2" in result
        assert "Value with" in result
        assert "pipe" in result

    def test_multiple_pipes_in_cell(self) -> None:
        """Test that multiple pipe characters are escaped in table cells."""
        html = """
        <table>
            <tr>
                <th>Header</th>
            </tr>
            <tr>
                <td>Value | with | multiple | pipes</td>
            </tr>
        </table>
        """
        BeautifulSoup(html, "html.parser")
        converter = TableConverter()
        result = converter.convert(html)

        # All pipe characters should be escaped (3 pipes in the content)
        assert result.count("\\|") == 3
        assert "Value" in result
        assert "with" in result
        assert "multiple" in result
        assert "pipes" in result

    def test_pipe_character_in_header(self) -> None:
        """Test that pipe characters are escaped in table header cells."""
        html = """
        <table>
            <tr>
                <th>Column | 1</th>
                <th>Column | 2</th>
            </tr>
            <tr>
                <td>Value 1</td>
                <td>Value 2</td>
            </tr>
        </table>
        """
        converter = TableConverter()
        result = converter.convert(html)

        # The pipe characters in headers should be escaped (2 pipes)
        assert result.count("\\|") == 2
        assert "Column" in result
        assert "Value 1" in result
        assert "Value 2" in result

    def test_table_without_pipes(self) -> None:
        """Test normal table conversion without pipe characters."""
        html = """
        <table>
            <tr>
                <th>Name</th>
                <th>Age</th>
            </tr>
            <tr>
                <td>John</td>
                <td>30</td>
            </tr>
        </table>
        """
        converter = TableConverter()
        result = converter.convert(html)

        assert "Name" in result
        assert "Age" in result
        assert "John" in result
        assert "30" in result
        # Should have proper table structure
        assert "|" in result
        assert "---" in result
        # Should have no escaped pipes
        assert "\\|" not in result

    def test_nested_table_outputs_html(self) -> None:
        """A table with a nested <table> inside a cell should output HTML, not pipe."""
        html = """
        <table>
            <tr>
                <th>Outer Header</th>
                <th>Details</th>
            </tr>
            <tr>
                <td>Row 1</td>
                <td>
                    <table>
                        <tr><td>Inner A</td><td>Inner B</td></tr>
                        <tr><td>Inner C</td><td>Inner D</td></tr>
                    </table>
                </td>
            </tr>
        </table>
        """
        converter = TableConverter()
        result = converter.convert(html)

        assert "<table>" in result or "<table" in result
        assert "<tr>" in result or "<tr" in result
        assert "<td>" in result or "<td" in result
        assert "Outer Header" in result
        assert "Row 1" in result
        assert "Inner A" in result
        assert "Inner D" in result

    def test_flat_table_still_produces_pipe(self) -> None:
        """A simple table without nesting should still produce a Markdown pipe table."""
        html = """
        <table>
            <tr><th>A</th><th>B</th></tr>
            <tr><td>1</td><td>2</td></tr>
        </table>
        """
        converter = TableConverter()
        result = converter.convert(html)

        assert "---" in result
        assert "A" in result
        assert "B" in result
        assert "1" in result
        assert "2" in result

