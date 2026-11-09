Clone the repository once and install the command once; the client can then start it from any working directory:

```sh
uv tool install --editable /path/to/megabonk_mods
```

Register the installed command in your MCP client (`megabonk-mcp` must be on its `PATH`; `uv tool update-shell` adds uv's tool directory):

```json
{
  "mcpServers": {
    "megabonk": {
      "command": "megabonk-mcp"
    }
  }
}
```

The server reads `.env`, `levels/` and the evidence folder from the checkout. With a non-editable install, add `"env": {"MEGABONK_REPO": "/path/to/megabonk_mods"}` to the entry.

The mod, running game, Python/uv setup and development harness must already be configured. Follow the <a href="https://github.com/pythoninthegrass/megabonk_mods/blob/main/docs/development.md#enabling" target="_blank" rel="noopener noreferrer">development harness guide</a> before connecting.
