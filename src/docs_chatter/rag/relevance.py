"""Relevance evaluation using LLM"""

import asyncio
import re
import logging
from langchain_anthropic import ChatAnthropic

from docs_chatter.config import settings

logger = logging.getLogger(__name__)

RELEVANCE_SYSTEM_PROMPT = """당신은 주어진 질의(Query)와 문서(Document)의 관련성을 평가하는 AI 어시스턴트입니다.

아래 제공된 질의와 문서를 분석하고, 관련성 점수를 0(관련 없음)에서 100(매우 관련 있음) 사이로 평가해주세요.

평가 기준:
- 0-20: 전혀 관련 없음
- 21-40: 약간의 관련성
- 41-60: 보통의 관련성
- 61-80: 높은 관련성
- 81-100: 매우 높은 관련성 (질문에 직접적인 답변 제공)

당신의 응답 형식은 다음과 같아야 합니다:
Relevance: <score>
Reason: <brief explanation>"""

RELEVANCE_USER_PROMPT = """질의(Query): {query}

문서(Document):
제목: {title}
내용: {content}

위 문서가 질의와 얼마나 관련이 있는지 평가해주세요."""


class RelevanceEvaluator:
    """Evaluate relevance of documents to query using LLM"""

    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-latest",
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=200,
        )

    async def evaluate_single(self, query: str, document: dict) -> dict:
        """Evaluate relevance of a single document"""
        title = document.get("title", "")
        content = document.get("parent_content", "")[:2000]  # Limit content size

        user_prompt = RELEVANCE_USER_PROMPT.format(
            query=query,
            title=title,
            content=content,
        )

        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [
                    {"role": "system", "content": RELEVANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            # Parse score from response
            score = self._parse_score(response.content)

            return {
                **document,
                "relevance_score": score,
                "relevance_response": response.content,
            }

        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            return {
                **document,
                "relevance_score": 0,
                "relevance_response": str(e),
            }

    async def evaluate_batch(
        self,
        query: str,
        documents: list[dict],
        threshold: float | None = None,
        max_docs: int | None = None,
    ) -> list[dict]:
        """Evaluate relevance for multiple documents concurrently"""
        threshold = threshold or settings.relevance_threshold
        max_docs = max_docs or settings.max_context_docs

        # Evaluate all documents concurrently
        tasks = [self.evaluate_single(query, doc) for doc in documents]
        results = await asyncio.gather(*tasks)

        # Filter by threshold
        filtered = [r for r in results if r["relevance_score"] > threshold]

        # Sort by relevance score
        filtered.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Limit to max docs
        return filtered[:max_docs]

    def _parse_score(self, response: str) -> float:
        """Parse relevance score from LLM response"""
        match = re.search(r"Relevance:\s*(\d+)", response)
        if match:
            return float(match.group(1))
        return 0.0
