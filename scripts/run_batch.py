#!/usr/bin/env python
"""Batch script for indexing Confluence documents"""

import argparse
import logging
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(__file__).replace("scripts/run_batch.py", "src"))

from docs_chatter.batch.indexer import BatchIndexer


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    parser = argparse.ArgumentParser(description="Index Confluence documents")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Indexing mode (default: incremental)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="For incremental mode: date since when to fetch updates (ISO format). Default: yesterday",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        indexer = BatchIndexer()

        if args.mode == "full":
            logger.info("Running full index...")
            stats = indexer.run_full_index()
        else:
            since = args.since
            if not since:
                # Default: yesterday
                since = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            logger.info(f"Running incremental index since {since}...")
            stats = indexer.run_incremental_index(since)

        logger.info(f"Indexing completed: {stats}")

    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
