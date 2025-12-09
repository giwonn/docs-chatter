"""Cohere embeddings wrapper"""

from langchain_cohere import CohereEmbeddings as LangChainCohereEmbeddings

from docs_chatter.config import settings


class CohereEmbeddings:
    """Wrapper for Cohere embeddings using LangChain"""

    def __init__(self, model: str = "embed-multilingual-v3.0"):
        self.model = model
        self._embeddings = LangChainCohereEmbeddings(
            cohere_api_key=settings.cohere_api_key,
            model=model,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents"""
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query"""
        return self._embeddings.embed_query(text)

    @property
    def dimension(self) -> int:
        """Return embedding dimension (1024 for Cohere v3)"""
        return 1024
