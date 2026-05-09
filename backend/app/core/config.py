from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG Knowledge Base"
    app_env: str = "development"
    openai_api_key: str = ""
    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag_knowledge_base"
    redis_url: str = "redis://localhost:6379/0"
    upload_storage_dir: str = "./storage/uploads"
    vector_store: str = "chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "knowledge_chunks"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    max_upload_size_mb: int = 50
    secret_key: str = "dev-secret-change-me"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
