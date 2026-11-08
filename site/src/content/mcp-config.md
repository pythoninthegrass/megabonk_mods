Launch the server from the repository root. In an MCP client, use `uv` as the command and the remaining arguments separately:

```sh
uv run --script scripts/mcp_server.py
```

Example client configuration (start the client from the repository root, or replace the script path with an absolute path):

```json
{
  "mcpServers": {
    "megabonk": {
      "command": "uv",
      "args": ["run", "--script", "scripts/mcp_server.py"]
    }
  }
}
```

The mod, running game, Python/uv setup and development harness must already be configured. Follow the <a href="https://github.com/pythoninthegrass/megabonk_mods/blob/main/docs/development.md#enabling" target="_blank" rel="noopener noreferrer">development harness guide</a> before connecting.
