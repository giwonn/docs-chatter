"""OpenSearch client for vector storage and hybrid search"""

from opensearchpy import OpenSearch
from typing import Any

from docs_chatter.config import settings
from docs_chatter.vectorstore.embeddings import CohereEmbeddings
from docs_chatter.rag.chunker import DocumentChunk


class OpenSearchClient:
    """Client for OpenSearch vector operations"""

    def __init__(self):
        self.client = OpenSearch(
            hosts=[
                {
                    "host": settings.opensearch_host,
                    "port": settings.opensearch_port,
                }
            ],
            http_auth=(settings.opensearch_username, settings.opensearch_password),
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
        )
        self.index_name = settings.opensearch_index
        self.embeddings = CohereEmbeddings()

    def create_index(self) -> None:
        """Create the index with proper mappings for hybrid search"""
        if self.client.indices.exists(index=self.index_name):
            return

        mappings = {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
                "analysis": {
                    "analyzer": {
                        "korean_analyzer": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": ["lowercase"],
                        }
                    }
                },
            },
            "mappings": {
                "properties": {
                    "page_id": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "title": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                    },
                    "url": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                    },
                    "parent_content": {"type": "text"},
                    "content_embedding": {
                        "type": "knn_vector",
                        "dimension": self.embeddings.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "nmslib",
                        },
                    },
                }
            },
        }

        self.client.indices.create(index=self.index_name, body=mappings)

    def delete_index(self) -> None:
        """Delete the index"""
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Index document chunks with embeddings"""
        if not chunks:
            return

        # Generate embeddings in batch
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embeddings.embed_documents(texts)

        # Bulk index
        actions = []
        for chunk, embedding in zip(chunks, embeddings):
            doc_id = f"{chunk.page_id}_{chunk.chunk_index}"

            action = {"index": {"_index": self.index_name, "_id": doc_id}}
            document = {
                "page_id": chunk.page_id,
                "chunk_index": chunk.chunk_index,
                "title": chunk.title,
                "url": chunk.url,
                "content": chunk.content,
                "parent_content": chunk.parent_content,
                "content_embedding": embedding,
            }

            actions.append(action)
            actions.append(document)

        if actions:
            self.client.bulk(body=actions, refresh=True)

    def delete_by_page_id(self, page_id: str) -> None:
        """Delete all chunks for a page"""
        query = {"query": {"term": {"page_id": page_id}}}
        self.client.delete_by_query(index=self.index_name, body=query)

    def hybrid_search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (lexical + neural)"""
        top_k = top_k or settings.search_top_k

        # Get query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Hybrid query
        search_query = {
            "_source": ["page_id", "chunk_index", "title", "url", "content", "parent_content"],
            "size": top_k,
            "query": {
                "hybrid": {
                    "queries": [
                        # Lexical search
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title", "content"],
                                "analyzer": "korean_analyzer",
                                "minimum_should_match": "80%",
                                "operator": "or",
                            }
                        },
                        # Neural search
                        {
                            "knn": {
                                "content_embedding": {
                                    "vector": query_embedding,
                                    "k": top_k,
                                }
                            }
                        },
                    ]
                }
            },
        }

        try:
            response = self.client.search(
                index=self.index_name,
                body=search_query,
            )
        except Exception:
            # Fallback: if hybrid not supported, use separate queries
            response = self._fallback_search(query, query_embedding, top_k)

        return self._parse_results(response)

    def _fallback_search(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int,
    ) -> dict:
        """Fallback search without hybrid query"""
        # KNN search only
        search_query = {
            "_source": ["page_id", "chunk_index", "title", "url", "content", "parent_content"],
            "size": top_k,
            "query": {
                "knn": {
                    "content_embedding": {
                        "vector": query_embedding,
                        "k": top_k,
                    }
                }
            },
        }

        return self.client.search(index=self.index_name, body=search_query)

    def _parse_results(self, response: dict) -> list[dict[str, Any]]:
        """Parse search response into list of results"""
        results = []
        hits = response.get("hits", {}).get("hits", [])

        for hit in hits:
            result = hit["_source"].copy()
            result["_score"] = hit.get("_score", 0)
            results.append(result)

        return results
