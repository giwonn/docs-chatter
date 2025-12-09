"""Batch indexer for Confluence documents"""

import logging
from datetime import datetime

from docs_chatter.confluence.client import ConfluenceClient, ConfluencePage
from docs_chatter.confluence.converter import HTMLConverter
from docs_chatter.rag.chunker import DocumentChunker
from docs_chatter.vectorstore.opensearch import OpenSearchClient

logger = logging.getLogger(__name__)


class BatchIndexer:
    """Batch process to index Confluence documents into OpenSearch"""

    def __init__(self):
        self.confluence = ConfluenceClient()
        self.converter = HTMLConverter()
        self.chunker = DocumentChunker()
        self.opensearch = OpenSearchClient()

    def run_full_index(self) -> dict:
        """Run full indexing of all configured spaces"""
        logger.info("Starting full index...")
        start_time = datetime.now()

        # Ensure index exists
        self.opensearch.create_index()

        # Fetch all pages
        pages = self.confluence.get_all_pages()
        logger.info(f"Found {len(pages)} pages to index")

        # Process and index
        stats = self._process_pages(pages)

        elapsed = (datetime.now() - start_time).total_seconds()
        stats["elapsed_seconds"] = elapsed
        logger.info(f"Full index completed in {elapsed:.2f}s: {stats}")

        return stats

    def run_incremental_index(self, since: str) -> dict:
        """Run incremental indexing since a given date

        Args:
            since: ISO format date string (e.g., "2024-01-01")
        """
        logger.info(f"Starting incremental index since {since}...")
        start_time = datetime.now()

        # Ensure index exists
        self.opensearch.create_index()

        # Fetch updated pages from all spaces
        pages = []
        from docs_chatter.config import settings

        for space_key in settings.space_keys_list:
            updated = self.confluence.get_updated_pages_since(space_key, since)
            pages.extend(updated)

        logger.info(f"Found {len(pages)} updated pages")

        # Delete existing chunks for updated pages
        for page in pages:
            self.opensearch.delete_by_page_id(page.id)

        # Process and index
        stats = self._process_pages(pages)

        elapsed = (datetime.now() - start_time).total_seconds()
        stats["elapsed_seconds"] = elapsed
        logger.info(f"Incremental index completed in {elapsed:.2f}s: {stats}")

        return stats

    def _process_pages(self, pages: list[ConfluencePage]) -> dict:
        """Process pages: convert, chunk, and index"""
        stats = {
            "pages_processed": 0,
            "chunks_indexed": 0,
            "errors": 0,
        }

        for page in pages:
            try:
                # Convert HTML to markdown and plain text
                markdown = self.converter.to_markdown(page.html_content)
                plain_text = self.converter.to_plain_text(page.html_content)

                if not plain_text.strip():
                    logger.warning(f"Skipping empty page: {page.title}")
                    continue

                # Chunk the document
                chunks = self.chunker.chunk_document(
                    page_id=page.id,
                    title=page.title,
                    url=page.url,
                    plain_text=plain_text,
                    markdown=markdown,
                )

                if not chunks:
                    continue

                # Index chunks
                self.opensearch.index_chunks(chunks)

                stats["pages_processed"] += 1
                stats["chunks_indexed"] += len(chunks)

                logger.debug(f"Indexed page '{page.title}' with {len(chunks)} chunks")

            except Exception as e:
                logger.error(f"Error processing page '{page.title}': {e}")
                stats["errors"] += 1

        return stats

    def reindex_page(self, page_id: str) -> bool:
        """Reindex a single page by ID"""
        try:
            page = self.confluence.get_page_by_id(page_id)
            if not page:
                logger.warning(f"Page not found: {page_id}")
                return False

            # Delete existing chunks
            self.opensearch.delete_by_page_id(page_id)

            # Process and index
            self._process_pages([page])
            return True

        except Exception as e:
            logger.error(f"Error reindexing page {page_id}: {e}")
            return False
