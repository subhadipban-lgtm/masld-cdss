"""Application configuration using pydantic-settings.

All environment variables are loaded with sensible defaults suitable
for the MASLD DrugScope production deployment.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the MASLD DrugScope backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Redis & Database ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./masld_drugscope.db"

    # ── Reference Data Paths ──────────────────────────────────────────
    reference_data_dir: str = "/app/reference_data"
    model_weights_path: str = "/app/reference_data/model_weights/graphsage_v1.pt"
    kg_edge_list_path: str = "/app/reference_data/knowledge_graph/edge_list.tsv"
    normalization_stats_path: str = "/app/reference_data/model_weights/normalization_stats.json"

    # ── Upload Limits ─────────────────────────────────────────────────
    max_upload_size_mb: int = 500
    upload_cleanup_hours: int = 24

    # ── Logging ───────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file_path: str = "/app/logs/masld_pipeline.log"

    # ── Versioning ────────────────────────────────────────────────────
    pipeline_version: str = "1.0.0"
    model_version: str = "v1.0.0-production"

    # ── External Tool Paths ───────────────────────────────────────────
    fastqc_path: str = "fastqc"
    fastp_path: str = "fastp"
    salmon_path: str = "salmon"
    gencode_version: str = "44"
    salmon_index_dir: str = "/app/reference_data/salmon_index/gencode_v44"

    # ── Derived Paths ─────────────────────────────────────────────────
    @property
    def reference_data_path(self) -> Path:
        """Return the reference data directory as a Path object."""
        return Path(self.reference_data_dir)

    @property
    def model_weights_file(self) -> Path:
        """Return the model weights path as a Path object."""
        return Path(self.model_weights_path)

    @property
    def kg_edge_list_file(self) -> Path:
        """Return the knowledge graph edge list path as a Path object."""
        return Path(self.kg_edge_list_path)

    @property
    def salmon_index_path(self) -> Path:
        """Return the Salmon index directory as a Path object."""
        return Path(self.salmon_index_dir)

    @property
    def tx2gene_path(self) -> Path:
        """Return the path to the transcript-to-gene mapping TSV."""
        return (
            self.reference_data_path
            / f"gencode_v{self.gencode_version}"
            / "tx2gene.tsv"
        )

    @property
    def max_upload_size_bytes(self) -> int:
        """Return maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()