"""Locates the repository checkout the harness reads `.env`, `levels/`, evidence and `taskfile.yml` from."""

import os
from collections.abc import Mapping
from pathlib import Path

REPO_ENV = "MEGABONK_REPO"


class CheckoutNotFound(RuntimeError):
    pass


def is_checkout(path: Path) -> bool:
    return (path / "taskfile.yml").is_file() and (path / "src" / "megabonk_harness").is_dir()


def _walk_up(start: Path) -> Path | None:
    return next((d for d in [start, *start.parents] if is_checkout(d)), None)


def find_checkout(cwd: Path, module_file: Path, environ: Mapping[str, str]) -> Path:
    """Override first, then the working directory's ancestors, then the tree this module was loaded from."""
    override = environ.get(REPO_ENV)
    if override:
        root = Path(override).expanduser().resolve()
        if not is_checkout(root):
            raise CheckoutNotFound(f"{REPO_ENV}={root} is not a megabonk_mods checkout (no taskfile.yml or src/megabonk_harness)")
        return root
    found = _walk_up(cwd.resolve()) or _walk_up(module_file.resolve().parent)
    if found is None:
        raise CheckoutNotFound(
            f"no megabonk_mods checkout found from {cwd} or {module_file}; clone the repository and set {REPO_ENV} to it, "
            "or install with `uv tool install --editable <checkout>`"
        )
    return found


def repo_root() -> Path:
    return find_checkout(Path.cwd(), Path(__file__), os.environ)
