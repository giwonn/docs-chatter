"""RAG chain for question answering"""

import asyncio
import logging
from langchain_anthropic import ChatAnthropic

from docs_chatter.config import settings
from docs_chatter.rag.retriever import HybridRetriever
from docs_chatter.rag.relevance import RelevanceEvaluator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 사내 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.

주어진 참고 문서를 바탕으로 질문에 정확하게 답변해주세요.

답변 규칙:
1. 참고 문서에 있는 내용만을 바탕으로 답변하세요.
2. 문서에서 답을 찾을 수 없다면 "해당 정보를 찾을 수 없습니다"라고 답변하세요.
3. 답변은 명확하고 간결하게 작성하세요.
4. 가능하면 관련 문서의 제목을 언급해주세요.
5. 추측하거나 문서에 없는 내용을 만들어내지 마세요."""

USER_PROMPT_TEMPLATE = """질문: {query}

참고 문서:
{context}

위 참고 문서를 바탕으로 질문에 답변해주세요."""


class RAGChain:
    """RAG chain combining retrieval, relevance evaluation, and generation"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.relevance_evaluator = RelevanceEvaluator()
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    async def aquery(self, query: str) -> dict:
        """Process a query through the RAG pipeline

        Returns:
            dict with keys: answer, sources, context_docs
        """
        # Step 1: Retrieve
        logger.info(f"Retrieving documents for query: {query}")
        retrieved = self.retriever.retrieve(query)

        if not retrieved:
            return {
                "answer": "관련 문서를 찾을 수 없습니다.",
                "sources": [],
                "context_docs": [],
            }

        logger.info(f"Retrieved {len(retrieved)} documents")

        # Step 2: Relevance evaluation
        logger.info("Evaluating relevance...")
        relevant_docs = await self.relevance_evaluator.evaluate_batch(query, retrieved)

        if not relevant_docs:
            return {
                "answer": "질문과 관련된 문서를 찾을 수 없습니다.",
                "sources": [],
                "context_docs": [],
            }

        logger.info(f"Found {len(relevant_docs)} relevant documents")

        # Step 3: Build context
        context = self._build_context(relevant_docs)

        # Step 4: Generate answer
        logger.info("Generating answer...")
        answer = await self._generate_answer(query, context)

        # Build sources list
        sources = [
            {"title": doc["title"], "url": doc["url"]}
            for doc in relevant_docs
        ]

        return {
            "answer": answer,
            "sources": sources,
            "context_docs": relevant_docs,
        }

    def query(self, query: str) -> dict:
        """Synchronous wrapper for aquery"""
        return asyncio.run(self.aquery(query))

    def _build_context(self, documents: list[dict]) -> str:
        """Build context string from relevant documents"""
        context_parts = []

        for i, doc in enumerate(documents, 1):
            context_parts.append(f"[문서 {i}] {doc['title']}")
            context_parts.append(doc["parent_content"][:3000])  # Limit per doc
            context_parts.append("")

        return "\n".join(context_parts)

    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using LLM"""
        user_prompt = USER_PROMPT_TEMPLATE.format(
            query=query,
            context=context,
        )

        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.content

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"답변 생성 중 오류가 발생했습니다: {e}"
