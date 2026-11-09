Clone the repository once, then register the server with `uvx`; there is nothing to install by hand and no machine-specific path in the entry:

```json
{
  "mcpServers": {
    "megabonk": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/pythoninthegrass/megabonk_mods", "megabonk-mcp"],
      "env": { "MEGABONK_REPO": "${MEGABONK_REPO:-}" }
    }
  }
}
```

The server reads `.env`, `levels/` and the evidence folder from your clone. It finds it from the directory the client starts in (any folder inside the clone), or from `MEGABONK_REPO` when the client starts elsewhere; export that once in your shell profile (`export MEGABONK_REPO=/path/to/megabonk_mods`). `uvx` caches the server code per commit, so run `uv cache clean megabonk-mods` after pulling a change to it.

The mod, running game, Python/uv setup and development harness must already be configured. Follow the <a href="https://github.com/pythoninthegrass/megabonk_mods/blob/main/docs/development.md#enabling" target="_blank" rel="noopener noreferrer">development harness guide</a> before connecting.
