"""Unit tests for api_clients module."""

import urllib.parse
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests
from atlassian.errors import ApiError

from confluence_markdown_exporter.api_clients import ApiClientFactory
from confluence_markdown_exporter.api_clients import AuthNotConfiguredError
from confluence_markdown_exporter.api_clients import ConfluenceRef
from confluence_markdown_exporter.api_clients import _install_request_logging
from confluence_markdown_exporter.api_clients import get_confluence_instance
from confluence_markdown_exporter.api_clients import log_api_response_hook
from confluence_markdown_exporter.api_clients import parse_confluence_path
from confluence_markdown_exporter.api_clients import response_hook
from confluence_markdown_exporter.api_clients import routing_path_for_parse
from confluence_markdown_exporter.utils.app_data_store import ApiDetails
from confluence_markdown_exporter.utils.app_data_store import AtlassianSdkConnectionConfig
from confluence_markdown_exporter.utils.app_data_store import ConfigModel
from tests.conftest import SAMPLE_CONFLUENCE_URL

_PARSE_CONFLUENCE_PATH_CASES = [
    (
        "https://company.atlassian.net/wiki/spaces/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "https://company.atlassian.net/wiki/spaces/SPACEKEY/pages/123456789/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789, page_title="Page Title"),
    ),
    (
        "https://company.atlassian.net/wiki/spaces/SPACEKEY/pages/sddssd/Page+Title",
        None,
    ),
    (
        "https://company.atlassian.net/wiki/spaces/SPACEKEY/overview",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "https://api.atlassian.com/ex/confluence/CLOUDID/wiki/spaces/SPACEKEY/pages/123456789/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789, page_title="Page Title"),
    ),
    (
        "https://api.atlassian.com/ex/confluence/1232132-12312312-21321332/wiki/spaces/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "https://api.atlassian.com/ex/confluence/1232132-12312312-21321332/wiki/spaces/SPACEKEY/pages/123456789",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789),
    ),
    (
        "/wiki/spaces/SPACEKEY/",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "/wiki/spaces/SPACEKEY/overview",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "/wiki/spaces/SPACEKEY/pages/123456789/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789, page_title="Page Title"),
    ),
    (
        "/ex/confluence/CLOUDID/wiki/spaces/SPACEKEY/pages/123456789/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789, page_title="Page Title"),
    ),
    (
        "/ex/confluence/1232132-12312312-21321332/wiki/spaces/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "/ex/confluence/1232132-12312312-21321332/wiki/spaces/SPACEKEY/pages/123456789",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789),
    ),
    (
        "https://confluence.company.com/display/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "https://confluence.company.com/display/SPACEKEY/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_title="Page Title"),
    ),
    (
        "https://confluence.company.com/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "https://confluence.company.com/SPACEKEY/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_title="Page Title"),
    ),
    (
        "https://company.atlassian.net/display/SPACEKEY/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_title="Page Title"),
    ),
    (
        "https://company.atlassian.net/SPACEKEY/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_title="Page Title"),
    ),
    (
        "/display/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "/display/SPACEKEY/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_title="Page Title"),
    ),
    (
        "/SPACEKEY",
        ConfluenceRef(space_key="SPACEKEY"),
    ),
    (
        "/SPACEKEY/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_title="Page Title"),
    ),
    (
        "https://wiki.aaa.aaa/spaces/SPACEKEY/pages/123456789/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789, page_title="Page Title"),
    ),
    (
        "/spaces/SPACEKEY/pages/123456789/Page+Title",
        ConfluenceRef(space_key="SPACEKEY", page_id=123456789, page_title="Page Title"),
    ),
]


class TestParseConfluencePath:
    """Test cases for parse_confluence_path function."""

    @pytest.mark.parametrize(("url", "expected"), _PARSE_CONFLUENCE_PATH_CASES)
    def test_parse_confluence_path(self, url: str, expected: ConfluenceRef | None) -> None:
        path = urllib.parse.urlparse(url).path if "://" in url else url
        result = parse_confluence_path(path)
        if expected is None:
            assert result is None
        else:
            assert result is not None
            assert result.model_dump() == expected.model_dump()


_ROUTING_PATH_FOR_PARSE_CASES = [
    (
        "/confluence/spaces/SPACEKEY/pages/123456789/Page+Title",
        "https://corp.example.com/confluence",
        "/spaces/SPACEKEY/pages/123456789/Page+Title",
    ),
    (
        "/confluence/spaces/SPACEKEY/overview",
        "https://corp.example.com/confluence",
        "/spaces/SPACEKEY/overview",
    ),
    (
        "/wiki/spaces/SPACEKEY/pages/1/T",
        "https://company.atlassian.net",
        "/wiki/spaces/SPACEKEY/pages/1/T",
    ),
    (
        "/spaces/SPACEKEY/pages/1/T",
        "https://wiki.aaa.aaa",
        "/spaces/SPACEKEY/pages/1/T",
    ),
    (
        "/ex/confluence/my-cloud-id/wiki/spaces/KEY/pages/42/x",
        "https://api.atlassian.com/ex/confluence/my-cloud-id",
        "/wiki/spaces/KEY/pages/42/x",
    ),
    (
        "/other/spaces/SPACEKEY/pages/1/T",
        "https://corp.example.com/confluence",
        "/other/spaces/SPACEKEY/pages/1/T",
    ),
]


class TestRoutingPathForParse:
    """Strip servlet context before parse_confluence_path."""

    @pytest.mark.parametrize(("path", "base_url", "expected"), _ROUTING_PATH_FOR_PARSE_CASES)
    def test_routing_path_for_parse(self, path: str, base_url: str, expected: str) -> None:
        assert routing_path_for_parse(path, base_url) == expected

    def test_empty_path_unchanged(self) -> None:
        assert routing_path_for_parse("", "https://h/confluence") == ""

    def test_strip_then_parse_dc_style(self) -> None:
        base = "https://confluence.example.com/confluence"
        raw = "/confluence/spaces/POINTSERVICE/pages/6409994109/Spec"
        routed = routing_path_for_parse(raw, base)
        ref = parse_confluence_path(routed)
        assert ref is not None
        assert ref.space_key == "POINTSERVICE"
        assert ref.page_id == 6409994109
        assert ref.page_title == "Spec"


class TestPageFromUrlContextPath:
    """Page.from_url resolves browser URLs with servlet context."""

    @patch("confluence_markdown_exporter.confluence.Page.from_id")
    def test_page_from_url_strips_confluence_context(
        self, mock_from_id: MagicMock
    ) -> None:
        from confluence_markdown_exporter.confluence import Page

        mock_page = MagicMock()
        mock_from_id.return_value = mock_page

        url = "https://internal.example.com/confluence/spaces/MYSPACE/pages/9876543210/Title+Here"
        result = Page.from_url(url)

        mock_from_id.assert_called_once_with(9876543210, "https://internal.example.com/confluence")
        assert result is mock_page


class TestSpaceFromUrlContextPath:
    """Space.from_url resolves browser URLs with servlet context."""

    @patch("confluence_markdown_exporter.confluence.Space.from_key")
    def test_space_from_url_strips_confluence_context(
        self, mock_from_key: MagicMock
    ) -> None:
        from confluence_markdown_exporter.confluence import Space

        mock_space = MagicMock()
        mock_from_key.return_value = mock_space

        url = "https://internal.example.com/confluence/spaces/PROJ/overview"
        result = Space.from_url(url)

        mock_from_key.assert_called_once_with("PROJ", "https://internal.example.com/confluence")
        assert result is mock_space


class TestInstallRequestLogging:
    """Tests for _install_request_logging (pre-request console log)."""

    @patch("confluence_markdown_exporter.api_clients.console")
    def test_prints_before_send(self, mock_console: MagicMock) -> None:
        """Wrapped send prints method and URL before dispatching the request."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        original_send = MagicMock(return_value=mock_response)

        session = requests.Session()
        session.send = original_send  # type: ignore[method-assign]
        _install_request_logging(session)

        prepared = requests.Request("GET", "https://example.com/rest/api/content/1").prepare()
        result = session.send(prepared)

        assert result is mock_response
        original_send.assert_called_once_with(prepared)
        mock_console.print.assert_called_once()
        printed = mock_console.print.call_args[0][0]
        assert "GET" in printed
        assert "example.com" in printed
        assert "..." in printed
        assert mock_console.print.call_args[1].get("markup") is False


class TestLogApiResponseHook:
    """Tests for log_api_response_hook."""

    @patch("confluence_markdown_exporter.api_clients.console")
    def test_prints_method_url_status(self, mock_console: MagicMock) -> None:
        """Every response prints method, URL, and status to the Rich console."""
        response = MagicMock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://example.com/confluence/rest/api/content/1"
        req = MagicMock()
        req.method = "GET"
        req.url = "https://example.com/confluence/rest/api/content/1?expand=body.view"
        response.request = req

        result = log_api_response_hook(response)

        assert result is response
        mock_console.print.assert_called_once()
        printed = mock_console.print.call_args[0][0]
        assert "GET" in printed
        assert "expand=body.view" in printed
        assert "HTTP 200" in printed
        assert mock_console.print.call_args[1].get("markup") is False


class TestResponseHook:
    """Test cases for response_hook function."""

    def test_successful_response(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that successful responses don't log warnings."""
        response = MagicMock(spec=requests.Response)
        response.ok = True
        response.status_code = 200

        result = response_hook(response)

        assert result == response
        assert len(caplog.records) == 0

    def test_failed_response(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that failed responses log warnings."""
        response = MagicMock(spec=requests.Response)
        response.ok = False
        response.status_code = 404
        response.url = "https://test.atlassian.net/api/test"
        response.headers = {"Content-Type": "application/json"}

        result = response_hook(response)

        assert result == response
        assert len(caplog.records) == 1
        log_record = caplog.records[0]
        expected_msg = "Request to https://test.atlassian.net/api/test failed with status 404"
        assert expected_msg in log_record.message
        assert "Response headers: {'Content-Type': 'application/json'}" in log_record.message


class TestApiClientFactory:
    """Test cases for ApiClientFactory class."""

    def test_init(self) -> None:
        """Test ApiClientFactory initialization stores an AtlassianSdkConnectionConfig."""
        config = AtlassianSdkConnectionConfig()
        factory = ApiClientFactory(config)
        assert factory.connection_config == config
        assert isinstance(factory.connection_config, AtlassianSdkConnectionConfig)

    @patch("confluence_markdown_exporter.api_clients.ConfluenceApiSdk")
    def test_create_confluence_success(
        self, mock_confluence_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test successful Confluence client creation."""
        mock_instance = MagicMock()
        mock_instance.get_all_spaces.return_value = [{"key": "TEST"}]
        mock_confluence_sdk.return_value = mock_instance

        sdk_config = AtlassianSdkConnectionConfig()
        factory = ApiClientFactory(sdk_config)

        result = factory.create_confluence(SAMPLE_CONFLUENCE_URL, sample_api_details)

        assert result == mock_instance
        mock_confluence_sdk.assert_called_once_with(
            url=SAMPLE_CONFLUENCE_URL,
            username=sample_api_details.username.get_secret_value(),
            password=sample_api_details.api_token.get_secret_value(),
            token=sample_api_details.pat.get_secret_value(),
            **sdk_config.model_dump(),
        )
        mock_instance.get_all_spaces.assert_called_once_with(limit=1)

    @patch("confluence_markdown_exporter.api_clients.ConfluenceApiSdk")
    def test_create_confluence_connection_failure(
        self, mock_confluence_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test Confluence client creation with connection failure."""
        mock_instance = MagicMock()
        mock_instance.get_all_spaces.side_effect = ApiError("Connection failed")
        mock_confluence_sdk.return_value = mock_instance

        factory = ApiClientFactory(AtlassianSdkConnectionConfig())

        with pytest.raises(ConnectionError, match="Confluence connection failed"):
            factory.create_confluence(SAMPLE_CONFLUENCE_URL, sample_api_details)

    @patch("confluence_markdown_exporter.api_clients.JiraApiSdk")
    def test_create_jira_success(
        self, mock_jira_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test successful Jira client creation."""
        mock_instance = MagicMock()
        mock_instance.get_all_projects.return_value = [{"key": "TEST"}]
        mock_jira_sdk.return_value = mock_instance

        sdk_config = AtlassianSdkConnectionConfig()
        factory = ApiClientFactory(sdk_config)

        result = factory.create_jira(SAMPLE_CONFLUENCE_URL, sample_api_details)

        assert result == mock_instance
        mock_jira_sdk.assert_called_once_with(
            url=SAMPLE_CONFLUENCE_URL,
            username=sample_api_details.username.get_secret_value(),
            password=sample_api_details.api_token.get_secret_value(),
            token=sample_api_details.pat.get_secret_value(),
            **sdk_config.model_dump(),
        )
        mock_instance.get_all_projects.assert_called_once()

    @patch("confluence_markdown_exporter.api_clients.JiraApiSdk")
    def test_create_jira_connection_failure(
        self, mock_jira_sdk: MagicMock, sample_api_details: ApiDetails
    ) -> None:
        """Test Jira client creation with connection failure."""
        mock_instance = MagicMock()
        mock_instance.get_all_projects.side_effect = ApiError("Connection failed")
        mock_jira_sdk.return_value = mock_instance

        factory = ApiClientFactory(AtlassianSdkConnectionConfig())

        with pytest.raises(ConnectionError, match="Jira connection failed"):
            factory.create_jira(SAMPLE_CONFLUENCE_URL, sample_api_details)


class TestGetConfluenceInstance:
    """Test cases for get_confluence_instance function."""

    @patch("confluence_markdown_exporter.api_clients._confluence_clients", {})
    @patch("confluence_markdown_exporter.api_clients.get_settings")
    @patch("confluence_markdown_exporter.api_clients.ApiClientFactory")
    def test_successful_connection(
        self,
        mock_factory_class: MagicMock,
        mock_get_settings: MagicMock,
        sample_config_model: ConfigModel,
    ) -> None:
        """Test successful Confluence instance creation."""
        mock_get_settings.return_value = sample_config_model
        mock_factory = MagicMock()
        mock_confluence = MagicMock()
        mock_factory.create_confluence.return_value = mock_confluence
        mock_factory_class.return_value = mock_factory

        result = get_confluence_instance(SAMPLE_CONFLUENCE_URL)

        assert result == mock_confluence
        mock_factory_class.assert_called_once_with(sample_config_model.connection_config)
        mock_factory.create_confluence.assert_called_once_with(
            SAMPLE_CONFLUENCE_URL,
            sample_config_model.auth.get_instance(SAMPLE_CONFLUENCE_URL),
        )

    @patch("confluence_markdown_exporter.api_clients._confluence_clients", {})
    @patch("confluence_markdown_exporter.api_clients.get_settings")
    @patch("confluence_markdown_exporter.api_clients.ApiClientFactory")
    def test_connection_failure_raises(
        self,
        mock_factory_class: MagicMock,
        mock_get_settings: MagicMock,
        sample_config_model: ConfigModel,
    ) -> None:
        """Test that a Confluence connection failure raises AuthNotConfiguredError."""
        mock_get_settings.return_value = sample_config_model

        mock_factory = MagicMock()
        mock_factory.create_confluence.side_effect = ConnectionError("Connection failed")
        mock_factory_class.return_value = mock_factory

        with pytest.raises(AuthNotConfiguredError) as exc_info:
            get_confluence_instance(SAMPLE_CONFLUENCE_URL)

        assert exc_info.value.url == SAMPLE_CONFLUENCE_URL
        assert exc_info.value.service == "Confluence"
        assert mock_factory.create_confluence.call_count == 1


class TestLazyHomepageResolution:
    """Verify homepage API calls are skipped when templates don't use {homepage_*}."""

    _ATT_PATH = (
        "{space_name}/attachments"
        "/{attachment_file_id}{attachment_extension}"
    )

    @patch("confluence_markdown_exporter.confluence.get_thread_confluence")
    @patch("confluence_markdown_exporter.confluence.settings")
    def test_space_from_key_skips_homepage_expand(
        self, mock_settings: MagicMock, mock_get_thread: MagicMock
    ) -> None:
        from confluence_markdown_exporter.confluence import Space

        Space.from_key.cache_clear()

        mock_settings.export.page_path = "{space_name}/{page_title}.md"
        mock_settings.export.attachment_path = self._ATT_PATH

        mock_client = MagicMock()
        mock_client.get_space.return_value = {
            "key": "TEST", "name": "Test", "description": {},
        }
        mock_get_thread.return_value = mock_client

        Space.from_key("TEST", "https://example.com")
        mock_client.get_space.assert_called_once_with("TEST", expand="")

        Space.from_key.cache_clear()

    @patch("confluence_markdown_exporter.confluence.get_thread_confluence")
    @patch("confluence_markdown_exporter.confluence.settings")
    def test_space_from_key_expands_homepage(
        self, mock_settings: MagicMock, mock_get_thread: MagicMock
    ) -> None:
        from confluence_markdown_exporter.confluence import Space

        Space.from_key.cache_clear()

        mock_settings.export.page_path = (
            "{space_name}/{homepage_title}/{page_title}.md"
        )
        mock_settings.export.attachment_path = self._ATT_PATH

        mock_client = MagicMock()
        mock_client.get_space.return_value = {
            "key": "TEST", "name": "Test", "description": {},
            "homepage": {"id": 999},
        }
        mock_get_thread.return_value = mock_client

        Space.from_key("TEST", "https://example.com")
        mock_client.get_space.assert_called_once_with(
            "TEST", expand="homepage"
        )

        Space.from_key.cache_clear()

    @patch("confluence_markdown_exporter.confluence.get_thread_confluence")
    @patch("confluence_markdown_exporter.confluence.settings")
    def test_template_vars_skips_homepage_fetch(
        self, mock_settings: MagicMock, mock_get_thread: MagicMock
    ) -> None:
        from confluence_markdown_exporter.confluence import Ancestor
        from confluence_markdown_exporter.confluence import Document
        from confluence_markdown_exporter.confluence import Space
        from confluence_markdown_exporter.confluence import Version

        mock_settings.export.page_path = "{space_name}/{page_title}.md"
        mock_settings.export.attachment_path = self._ATT_PATH

        space = Space(
            base_url="https://example.com",
            key="T", name="Test", description="", homepage=42,
        )

        class _Doc(Document):
            pass

        _Doc.model_rebuild(_types_namespace={"Ancestor": Ancestor})

        doc = _Doc(
            base_url="https://example.com",
            title="My Page",
            space=space,
            ancestors=[],
            version=Version.from_json({}),
        )

        tvars = doc._template_vars

        mock_get_thread.return_value.get_page_by_id.assert_not_called()
        assert tvars["homepage_id"] == ""
        assert tvars["homepage_title"] == ""
