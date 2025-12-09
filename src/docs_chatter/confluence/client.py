"""Confluence API client for fetching documents"""

from dataclasses import dataclass
from atlassian import Confluence

from docs_chatter.config import settings


@dataclass
class ConfluencePage:
    """Represents a Confluence page"""

    id: str
    title: str
    space_key: str
    url: str
    html_content: str
    last_modified: str
    author: str


class ConfluenceClient:
    """Client for interacting with Confluence API"""

    def __init__(self):
        self.client = Confluence(
            url=settings.confluence_url,
            username=settings.confluence_username,
            password=settings.confluence_api_token,
            cloud=True,
        )

    def get_all_pages_in_space(self, space_key: str) -> list[ConfluencePage]:
        """Fetch all pages in a space"""
        pages = []
        start = 0
        limit = 50

        while True:
            results = self.client.get_all_pages_from_space(
                space=space_key,
                start=start,
                limit=limit,
                expand="body.storage,version,history",
            )

            if not results:
                break

            for page in results:
                pages.append(self._parse_page(page, space_key))

            if len(results) < limit:
                break

            start += limit

        return pages

    def get_page_by_id(self, page_id: str) -> ConfluencePage | None:
        """Fetch a single page by ID"""
        page = self.client.get_page_by_id(
            page_id=page_id,
            expand="body.storage,version,history,space",
        )

        if not page:
            return None

        space_key = page.get("space", {}).get("key", "")
        return self._parse_page(page, space_key)

    def get_updated_pages_since(
        self, space_key: str, since: str
    ) -> list[ConfluencePage]:
        """Fetch pages updated since a given date (ISO format)"""
        cql = f'space = "{space_key}" AND lastModified >= "{since}"'
        pages = []
        start = 0
        limit = 50

        while True:
            results = self.client.cql(
                cql=cql,
                start=start,
                limit=limit,
                expand="body.storage,version,history",
            )

            if not results or not results.get("results"):
                break

            for result in results["results"]:
                pages.append(self._parse_page(result, space_key))

            if len(results["results"]) < limit:
                break

            start += limit

        return pages

    def _parse_page(self, page: dict, space_key: str) -> ConfluencePage:
        """Parse API response into ConfluencePage"""
        page_id = page.get("id", "")
        title = page.get("title", "")

        # Get HTML content
        body = page.get("body", {})
        html_content = body.get("storage", {}).get("value", "")

        # Get metadata
        version = page.get("version", {})
        last_modified = version.get("when", "")
        author = version.get("by", {}).get("displayName", "")

        # Build URL
        base_url = settings.confluence_url.rstrip("/")
        url = f"{base_url}/wiki/spaces/{space_key}/pages/{page_id}"

        return ConfluencePage(
            id=page_id,
            title=title,
            space_key=space_key,
            url=url,
            html_content=html_content,
            last_modified=last_modified,
            author=author,
        )

    def get_all_pages(self) -> list[ConfluencePage]:
        """Fetch all pages from configured spaces"""
        all_pages = []
        for space_key in settings.space_keys_list:
            pages = self.get_all_pages_in_space(space_key)
            all_pages.extend(pages)
        return all_pages
