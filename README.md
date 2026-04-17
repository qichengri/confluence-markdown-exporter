
Fork from  <a href="https://github.com/Spenhouet/confluence-markdown-exporter">Spenhouet/confluence-markdown-exporter</a>

Updated For 
- Onprem Confluence supports 
- MDX compatibilitys
- Table In Table -> Use HTML table.

This tool is an open source project released under the [MIT License](LICENSE).

## Install from Source

```bash
git clone https://github.com/Spenhouet/confluence-markdown-exporter.git
cd confluence-markdown-exporter
pip install -e .
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/Spenhouet/confluence-markdown-exporter.git
cd confluence-markdown-exporter
uv sync
```

After installation, the `cme` command is available from any directory (make sure the virtual environment is activated, or use `uv run cme`).

## Quick Start

```bash
# Configure Confluence credentials
cme config edit auth.confluence

# Set output directory
cme config set export.output_path=./output

# Export a page
cme pages https://company.atlassian.net/wiki/spaces/KEY/pages/123/Title

# Export a whole space
cme spaces https://company.atlassian.net/wiki/spaces/MYSPACE
```

Config values can also be overridden inline via environment variables using the `CME_` prefix:

```bash
CME_EXPORT__OUTPUT_PATH=./output cme pages https://...
```
