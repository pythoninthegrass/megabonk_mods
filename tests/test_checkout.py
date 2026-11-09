import pytest
from megabonk_harness import checkout
from megabonk_harness.checkout import REPO_ENV, CheckoutNotFound, find_checkout
from pathlib import Path


def make_checkout(root: Path) -> Path:
    (root / "src" / "megabonk_harness").mkdir(parents=True)
    (root / "taskfile.yml").write_text("version: '3'\n")
    return root


def test_env_override_wins_over_the_working_directory(tmp_path: Path) -> None:
    mine = make_checkout(tmp_path / "mine")
    other = make_checkout(tmp_path / "other")
    assert find_checkout(other, tmp_path / "cache" / "mod.py", {REPO_ENV: str(mine)}) == mine


def test_env_override_naming_a_non_checkout_fails_naming_it(tmp_path: Path) -> None:
    with pytest.raises(CheckoutNotFound, match=str(tmp_path / "nope")):
        find_checkout(tmp_path, tmp_path / "cache" / "mod.py", {REPO_ENV: str(tmp_path / "nope")})


def test_walks_up_from_a_nested_working_directory(tmp_path: Path) -> None:
    root = make_checkout(tmp_path / "repo")
    nested = root / "levels" / "deep"
    nested.mkdir(parents=True)
    assert find_checkout(nested, tmp_path / "cache" / "mod.py", {}) == root


def test_source_tree_copy_finds_its_checkout_from_an_unrelated_directory(tmp_path: Path) -> None:
    root = make_checkout(tmp_path / "repo")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    module = root / "src" / "megabonk_harness" / "checkout.py"
    assert find_checkout(elsewhere, module, {}) == root


def test_installed_copy_outside_any_checkout_fails_naming_the_override(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    cache_module = tmp_path / "uv-cache" / "site-packages" / "megabonk_harness" / "checkout.py"
    with pytest.raises(CheckoutNotFound, match=REPO_ENV):
        find_checkout(elsewhere, cache_module, {})


def test_installed_copy_uses_the_override_from_an_unrelated_directory(tmp_path: Path) -> None:
    root = make_checkout(tmp_path / "repo")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    cache_module = tmp_path / "uv-cache" / "site-packages" / "megabonk_harness" / "checkout.py"
    assert find_checkout(elsewhere, cache_module, {REPO_ENV: str(root)}) == root


def test_repo_root_reads_the_process_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_checkout(tmp_path / "repo")
    monkeypatch.setenv(REPO_ENV, str(root))
    assert checkout.repo_root() == root


def test_the_development_tree_is_a_checkout() -> None:
    assert (checkout.repo_root() / "taskfile.yml").is_file()
