"""Slack bot handler"""

import asyncio
import logging
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from docs_chatter.config import settings
from docs_chatter.rag.chain import RAGChain

logger = logging.getLogger(__name__)


class SlackBot:
    """Slack bot for RAG-based Q&A"""

    def __init__(self):
        self.app = App(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )
        self.rag_chain = RAGChain()
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers"""

        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle @mentions"""
            self._handle_question(event, say)

        @self.app.event("message")
        def handle_dm(event, say):
            """Handle direct messages"""
            # Only respond to DMs (no channel)
            if event.get("channel_type") == "im":
                self._handle_question(event, say)

    def _handle_question(self, event: dict, say):
        """Process a question and respond"""
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Remove bot mention from text
        query = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        if not query:
            say(
                text="질문을 입력해주세요!",
                channel=channel,
                thread_ts=thread_ts,
            )
            return

        logger.info(f"Question from {user}: {query}")

        # Send "thinking" message
        say(
            text="문서를 검색하고 있습니다...",
            channel=channel,
            thread_ts=thread_ts,
        )

        try:
            # Run RAG query
            result = asyncio.run(self.rag_chain.aquery(query))

            # Format response
            response = self._format_response(result)

            say(
                text=response,
                channel=channel,
                thread_ts=thread_ts,
            )

        except Exception as e:
            logger.error(f"Error processing question: {e}")
            say(
                text=f"오류가 발생했습니다: {e}",
                channel=channel,
                thread_ts=thread_ts,
            )

    def _format_response(self, result: dict) -> str:
        """Format RAG result as Slack message"""
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        parts = [answer]

        if sources:
            parts.append("\n\n*참고 문서:*")
            for source in sources[:5]:  # Limit to 5 sources
                title = source.get("title", "")
                url = source.get("url", "")
                parts.append(f"• <{url}|{title}>")

        return "\n".join(parts)

    def start(self):
        """Start the bot using Socket Mode"""
        logger.info("Starting Slack bot...")
        handler = SocketModeHandler(self.app, settings.slack_app_token)
        handler.start()
