"""HTML to Markdown/Plain Text converter"""

import re
from bs4 import BeautifulSoup
from markdownify import markdownify


class HTMLConverter:
    """Convert HTML content to Markdown and Plain Text"""

    @staticmethod
    def to_markdown(html: str) -> str:
        """Convert HTML to Markdown (for LLM context)"""
        if not html:
            return ""

        # Convert to markdown
        md = markdownify(html, heading_style="ATX", strip=["script", "style"])

        # Clean up
        md = HTMLConverter._clean_markdown(md)

        return md.strip()

    @staticmethod
    def to_plain_text(html: str) -> str:
        """Convert HTML to Plain Text (for embedding)"""
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator=" ")

        # Clean up
        text = HTMLConverter._clean_text(text)

        return text.strip()

    @staticmethod
    def _clean_markdown(md: str) -> str:
        """Clean up markdown content"""
        # Remove image tags
        md = re.sub(r"!\[.*?\]\(.*?\)", "", md)

        # Remove links but keep text: [text](url) -> text
        md = re.sub(r"\[(.*?)\]\([^\)]+\)", r"\1", md)

        # Remove duplicate punctuation: !!! -> !
        md = re.sub(r"([!?.,]){2,}", r"\1", md)

        # Remove empty lines
        md = re.sub(r"(?m)^\s*\n", "\n", md)

        # Collapse multiple newlines
        md = re.sub(r"\n{3,}", "\n\n", md)

        # Remove excessive whitespace
        md = re.sub(r"[ \t]+", " ", md)

        # Trim each line
        md = "\n".join(line.strip() for line in md.split("\n"))

        return md

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean up plain text content"""
        # Remove duplicate punctuation
        text = re.sub(r"([!?.,]){2,}", r"\1", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text
