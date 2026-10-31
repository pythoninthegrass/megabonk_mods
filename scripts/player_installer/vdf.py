"""Reader for Valve's KeyValues (.vdf) format, enough to inspect Steam's own files.

Only what the installer needs to read: libraryfolders.vdf for library paths and
localconfig.vdf for a game's launch options and forced Proton tool. Steam rewrites
localconfig.vdf while it runs, so nothing here writes it.
"""

from __future__ import annotations

from collections.abc import Iterable

COMMENT_PREFIXES = ("//", ";")


class VdfError(ValueError):
    """The file is not parseable KeyValues."""


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char in " \t\r\n":
            index += 1
            continue
        if char in "{}":
            tokens.append(char)
            index += 1
            continue
        if char == '"':
            end = text.find('"', index + 1)
            while end != -1 and text[end - 1] == "\\":
                end = text.find('"', end + 1)
            if end == -1:
                raise VdfError("unterminated quoted string")
            tokens.append(text[index + 1 : end].replace('\\"', '"'))
            index = end + 1
            continue
        if char == "/" and text.startswith("//", index):
            end = text.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        end = index
        while end < length and text[end] not in ' \t\r\n{}"':
            end += 1
        word = text[index:end]
        if word.startswith(COMMENT_PREFIXES):
            index = length
            continue
        tokens.append(word)
        index = end
    return tokens


def _parse(tokens: list[str], position: int, depth: int) -> tuple[dict, int]:
    result: dict = {}
    while position < len(tokens):
        token = tokens[position]
        if token == "}":
            if depth == 0:
                raise VdfError("unexpected '}'")
            return result, position + 1
        if token == "{":
            raise VdfError("'{' without a key")
        key = token
        position += 1
        if position >= len(tokens):
            raise VdfError(f"key {key!r} has no value")
        value = tokens[position]
        if value == "{":
            child, position = _parse(tokens, position + 1, depth + 1)
            result[key] = child
        elif value == "}":
            raise VdfError(f"key {key!r} has no value")
        else:
            result[key] = value
            position += 1
    if depth:
        raise VdfError("unexpected end of file: missing '}'")
    return result, position


def parse_vdf(text: str) -> dict:
    """Parse KeyValues text into nested dicts; scalar values stay strings."""
    parsed, _ = _parse(_tokenize(text), 0, 0)
    return parsed


def load_vdf(path) -> dict:
    from pathlib import Path

    return parse_vdf(Path(path).read_text(encoding="utf-8", errors="replace"))


def find_all(data: dict, path: Iterable[str]) -> list:
    """Every value under a key path; '*' matches any single key."""
    keys = list(path)
    current: list = [data]
    for key in keys:
        nxt: list = []
        for node in current:
            if not isinstance(node, dict):
                continue
            if key == "*":
                nxt.extend(node.values())
            elif key in node:
                nxt.append(node[key])
        current = nxt
    return [value for value in current if not isinstance(value, dict)]


def find(data: dict, path: Iterable[str]):
    hits = find_all(data, path)
    return hits[0] if hits else None


def _app_section(data: dict, app_id: str) -> dict | None:
    for prefix in (("Steam", "apps"), ("apps",), ()):
        node: object = data
        ok = True
        for key in (*prefix, str(app_id)):
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                ok = False
                break
        if ok and isinstance(node, dict):
            return node
    return None


def _app_field(data: dict, app_id: str, field: str) -> str | None:
    section = _app_section(data, app_id)
    if not section:
        return None
    value = section.get(field)
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def launch_options(data: dict, app_id: str) -> str | None:
    """The launch options Steam has for an app, or None when it has none."""
    return _app_field(data, app_id, "LaunchOptions")


def compat_force_tool(data: dict, app_id: str) -> str | None:
    """The Proton tool forced for an app in Steam's settings, or None."""
    return _app_field(data, app_id, "CompatForceTool")


def library_folder_paths(data: dict) -> list[str]:
    """Every library path from libraryfolders.vdf, in file order."""
    return [str(value) for value in find_all(data, ("libraryfolders", "*", "path"))]
