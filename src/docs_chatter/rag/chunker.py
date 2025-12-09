"""Document chunking with recursive splitting and overlap"""

from dataclasses import dataclass
from langchain.text_splitter import RecursiveCharacterTextSplitter

from docs_chatter.config import settings


@dataclass
class DocumentChunk:
    """Represents a chunk of a document"""

    page_id: str
    chunk_index: int
    title: str
    url: str
    content: str  # Plain text for embedding
    parent_content: str  # Markdown for LLM context


class DocumentChunker:
    """Split documents into chunks using recursive character splitting"""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_document(
        self,
        page_id: str,
        title: str,
        url: str,
        plain_text: str,
        markdown: str,
    ) -> list[DocumentChunk]:
        """Split a document into chunks"""
        if not plain_text.strip():
            return []

        # Split plain text for embedding
        text_chunks = self.splitter.split_text(plain_text)

        chunks = []
        for i, content in enumerate(text_chunks):
            chunk = DocumentChunk(
                page_id=page_id,
                chunk_index=i,
                title=title,
                url=url,
                content=content,
                parent_content=markdown,  # Keep full markdown as parent
            )
            chunks.append(chunk)

        return chunks

    def chunk_documents(
        self,
        documents: list[dict],
    ) -> list[DocumentChunk]:
        """Split multiple documents into chunks

        Args:
            documents: List of dicts with keys:
                - page_id, title, url, plain_text, markdown
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(
                page_id=doc["page_id"],
                title=doc["title"],
                url=doc["url"],
                plain_text=doc["plain_text"],
                markdown=doc["markdown"],
            )
            all_chunks.extend(chunks)
        return all_chunks
