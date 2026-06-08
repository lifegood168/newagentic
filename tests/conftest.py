import os
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    db_path = tmp_path / "test.db"
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("AGENTS_DIR", str(agents_dir))
    monkeypatch.setenv("LOG_FORMAT", "console")

    from app.internal.config import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()
