"""Configuration management using pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Confluence
    confluence_url: str
    confluence_username: str
    confluence_api_token: str
    confluence_space_keys: str  # comma-separated: "SPACE1,SPACE2"

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"
    opensearch_index: str = "wise-chatter"
    opensearch_use_ssl: bool = True
    opensearch_verify_certs: bool = False

    # Cohere (Embedding)
    cohere_api_key: str

    # Anthropic (LLM)
    anthropic_api_key: str

    # Slack
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str

    # RAG Settings
    chunk_size: int = 800
    chunk_overlap: int = 100
    search_top_k: int = 30
    relevance_threshold: float = 60.0
    score_threshold: float = 0.3
    max_context_docs: int = 10

    # LLM Settings
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    @property
    def space_keys_list(self) -> list[str]:
        """Parse comma-separated space keys into list"""
        return [s.strip() for s in self.confluence_space_keys.split(",") if s.strip()]


settings = Settings()
