# itential.mcp.mcp

Installs and manages the [Itential MCP Server](https://github.com/itential/itential-mcp)
as a `systemd` service on RHEL-family and Amazon Linux VMs.

The role handles Python installation (3.11, or the system Python on EL10 and later), virtual environment setup, system user
creation, config and credentials file management, and service lifecycle.

For full documentation, inventory variable reference, and example inventories see
the [collection README](https://github.com/itential/itential.mcp#readme).
