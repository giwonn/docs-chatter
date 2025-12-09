"""Hybrid retriever for RAG pipeline"""

from typing import Any
from docs_chatter.config import settings
from docs_chatter.vectorstore.opensearch import OpenSearchClient


class HybridRetriever:
    """Retriever that performs hybrid search and merges parent documents"""

    def __init__(self):
        self.opensearch = OpenSearchClient()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents using hybrid search

        Args:
            query: User query
            top_k: Number of results to retrieve
            score_threshold: Minimum score threshold

        Returns:
            List of search results with parent content merged
        """
        top_k = top_k or settings.search_top_k
        score_threshold = score_threshold or settings.score_threshold

        # Perform hybrid search
        results = self.opensearch.hybrid_search(query, top_k)

        # Filter by score
        filtered = [r for r in results if r.get("_score", 0) > score_threshold]

        # Merge parent documents (deduplicate by page_id)
        merged = self._merge_parents(filtered)

        return merged

    def _merge_parents(self, results: list[dict]) -> list[dict]:
        """Merge chunks from the same parent document"""
        # Group by page_id
        pages: dict[str, dict] = {}

        for result in results:
            page_id = result["page_id"]

            if page_id not in pages:
                pages[page_id] = {
                    "page_id": page_id,
                    "title": result["title"],
                    "url": result["url"],
                    "parent_content": result["parent_content"],
                    "chunks": [],
                    "max_score": result.get("_score", 0),
                }

            pages[page_id]["chunks"].append(
                {
                    "content": result["content"],
                    "chunk_index": result["chunk_index"],
                    "score": result.get("_score", 0),
                }
            )

            # Track max score for sorting
            if result.get("_score", 0) > pages[page_id]["max_score"]:
                pages[page_id]["max_score"] = result.get("_score", 0)

        # Sort by max score
        sorted_pages = sorted(pages.values(), key=lambda x: x["max_score"], reverse=True)

        return sorted_pages
