"""Local configuration shared by future application modules."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the local-only demonstration."""

    api_prefix: str = "/api/v1"
    data_dir: Path = Path.home() / ".astra" / "data"
    database_url: str | None = None
    automated_ingestion_enabled: bool = False


def get_settings() -> Settings:
    """Return local defaults without creating storage as a side effect."""

    configured_data_dir = os.environ.get("ASTRA_DATA_DIR")
    data_dir = (
        Path(configured_data_dir).expanduser()
        if configured_data_dir
        else Path.home() / ".astra" / "data"
    )
    return Settings(
        data_dir=data_dir,
        database_url=os.environ.get("ASTRA_DATABASE_URL"),
        automated_ingestion_enabled=os.environ.get("ASTRA_ENABLE_AUTOMATED_INGESTION") == "1",
    )
