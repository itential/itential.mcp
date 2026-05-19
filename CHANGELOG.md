# Changelog

## v0.1.0

### New Features

- Initial release of the `itential.mcp` Ansible collection
- `mcp` role installs and manages the Itential MCP Server as a systemd service
- Supports SSE and HTTP transport modes
- Supports basic auth and OAuth client credential authentication to Itential Platform
- Supports TLS connections to Itential Platform with public or private CA certificates
- Supports offline / air-gapped installation from a pre-staged wheel bundle
- `verify_mcp` playbook for pre-installation prerequisite checks
- `certify_mcp` playbook for post-installation validation with markdown report generation
- Example inventories for standard, fully-explicit, and offline deployments
