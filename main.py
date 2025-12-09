#!/usr/bin/env python
"""Main entry point for Docs Chatter Slack bot"""

import logging
import sys

# Add src to path
sys.path.insert(0, "src")

from docs_chatter.slack.bot import SlackBot


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Docs Chatter...")

    try:
        bot = SlackBot()
        bot.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
