"""Isolates every Python test from the developer's MEGABONK_* variables and the repo .env file."""

import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_megabonk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import game_paths

    for key in [key for key in os.environ if key.startswith("MEGABONK_")]:
        monkeypatch.delenv(key)
    monkeypatch.setattr(game_paths, "ENV_FILE", Path("/nonexistent/.env"))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
