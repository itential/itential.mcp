# Ansible Collection - itential.mcp

## Table of Contents

1. [Overview](#overview)
2. [Supported Configurations](#supported-configurations)
    1. [Transport Modes](#transport-modes)
    2. [Platform Authentication](#platform-authentication)
    3. [TLS](#tls)
3. [Prerequisites](#prerequisites)
    1. [Control Node Requirements](#control-node-requirements)
    2. [Target Server Requirements](#target-server-requirements)
    3. [Network Requirements](#network-requirements)
4. [Installing the Collection](#installing-the-collection)
5. [Running the Collection](#running-the-collection)
    1. [Verify Prerequisites](#verify-prerequisites)
    2. [Create an Inventory](#create-an-inventory)
    3. [Install and Configure](#install-and-configure)
    4. [Certify the Installation](#certify-the-installation)
6. [Inventory Variables Reference](#inventory-variables-reference)
    1. [Package Installation](#package-installation)
    2. [Server Configuration](#server-configuration)
    3. [Platform Connection](#platform-connection)
    4. [TLS](#tls-variables)
    5. [Offline Installation](#offline-variables)
7. [Example Inventories](#example-inventories)
8. [Offline Installation](#offline-installation)
9. [TLS Configuration](#tls-configuration)
10. [High Availability Platform](#high-availability-platform)
11. [Upgrading](#upgrading)

---

## Overview

The **Itential MCP Server** is a production-grade [Model Context Protocol](https://modelcontextprotocol.io)
server that bridges AI agents with the Itential Platform. It exposes 60+ tools across
categories including workflow execution, device configuration, compliance, lifecycle
management, and platform health — allowing AI assistants to interact with Itential
Platform through a standardized interface.

The `itential.mcp` collection installs and manages the Itential MCP Server as a
`systemd` service on a Linux VM. It handles:

- Installing Python 3.11 and creating a dedicated virtual environment
- Installing the `itential-mcp` package and its dependencies
- Creating a dedicated system user and configuring file permissions
- Writing the server configuration and credentials files
- Installing and enabling the `systemd` service
- Verifying prerequisites before installation
- Certifying the installation after deployment

**&#9432; Note:**
The collection targets VM deployments where multiple AI clients connect to a shared
MCP server over the network. For single-user local installations (e.g., Claude Desktop
on a developer laptop), install `itential-mcp` directly with `pip` and configure your
MCP client to run it as a local process.

---

## Supported Configurations

### Transport Modes

| Transport | Description | Use Case |
|-----------|-------------|----------|
| `sse` | Server-Sent Events over HTTP | Default. Widely supported by MCP clients. |
| `http` | Streamable HTTP | Newer MCP transport standard. |

**&#9432; Note:** `stdio` transport is not supported by this role. It is incompatible
with `systemd` service management.

### Platform Authentication

| Method | Variables | Description |
|--------|-----------|-------------|
| Basic auth | `mcp_platform_user`, `mcp_platform_password` | Default. Username and password. |
| OAuth | `mcp_platform_client_id`, `mcp_platform_client_secret` | Platform service account OAuth credentials. When both are set, basic auth variables are ignored. |

### TLS

The role supports connecting to an Itential Platform that uses TLS (HTTPS).

| Scenario | Variables |
|----------|-----------|
| Platform on HTTPS, public CA | `mcp_platform_tls: true`, `mcp_platform_port: 3443` |
| Platform on HTTPS, private CA | Above plus `mcp_platform_ca_bundle: /etc/pki/tls/certs/ca-bundle.crt` |
| Skip cert verification | `mcp_platform_tls: true`, `mcp_platform_disable_verify: true` |

**&#9432; Note:** The MCP server itself does not terminate TLS. If clients require
HTTPS to connect to the MCP server, place a reverse proxy (nginx, HAProxy) in front
of it.

---

## Prerequisites

### Control Node Requirements

| Component | Requirement |
|-----------|-------------|
| Ansible | >= 2.14 |
| Python | >= 3.9 |

### Target Server Requirements

| Component | Requirement |
|-----------|-------------|
| OS | RHEL 8/9, Rocky 8/9, Oracle Linux 8/9, Amazon Linux 2023 |
| Architecture | x86_64, aarch64 |
| RAM | 1 GB minimum |
| Disk | 2 GB free in `/opt` |
| systemd | Required |
| Privilege escalation | `sudo` access required (`become: true`) |

**&#9432; Note:** On Amazon Linux 2023, `python3.11-pip` must be added to
`mcp_python_packages` in addition to `python3.11`. See [Example Inventories](#example-inventories).

### Network Requirements

The target server must be able to reach:

| Destination | Port | Protocol | Required For |
|-------------|------|----------|--------------|
| `pypi.org` | 443 | TCP | Installing `itential-mcp` (online installs only) |
| Itential Platform host | 3000 or 3443 | TCP | Connecting to the Platform API |

MCP clients must be able to reach the target server on `mcp_port` (default: 8000).

---

## Installing the Collection

Install from Ansible Galaxy:

```bash
ansible-galaxy collection install itential.mcp
```

To install a specific version:

```bash
ansible-galaxy collection install itential.mcp:==0.1.0
```

---

## Running the Collection

### Verify Prerequisites

Run the verify playbook against your target server before installing. It checks
that Python 3.11 is available, the Platform host is reachable, and the MCP port
is not already in use.

```bash
ansible-playbook itential.mcp.verify_mcp -i your_inventory.yaml
```

### Create an Inventory

Copy one of the [example inventories](#example-inventories) and fill in the
required values:

- `mcp_platform_host` — hostname or IP of your Itential Platform
- `mcp_platform_user` / `mcp_platform_password` — Platform credentials (or OAuth equivalent)

### Install and Configure

```bash
ansible-playbook itential.mcp.mcp -i your_inventory.yaml
```

The playbook will:
1. Validate all variables
2. Install `python3.11` via `dnf`
3. Create a Python virtual environment at `/opt/itential-mcp/venv`
4. Install `itential-mcp` and its dependencies
5. Create the `itential-mcp` system user and group
6. Write `/etc/itential-mcp/mcp.conf` and `/etc/itential-mcp/itential-mcp.env`
7. Install and enable the `itential-mcp` systemd service
8. Assert the service is running before completing

### Certify the Installation

After a successful install, run the certify playbook to validate the deployment
and generate a markdown report on the control node.

```bash
ansible-playbook itential.mcp.certify_mcp -i your_inventory.yaml
```

The certify playbook checks:

- Service active state and enabled status
- Process running
- Port listening
- Config and credential file presence and permissions
- Installed version
- Available tool count
- Health endpoint (`/status/healthz`) — server liveness
- Readiness endpoint (`/status/readyz`) — live Platform connectivity

The markdown report is written to:
```
<playbook_dir>/certify-reports/mcp-certify-<hostname>.md
```

---

## Inventory Variables Reference

All variables have defaults and can be overridden in your inventory.

### Package Installation

| Variable | Default | Description |
|----------|---------|-------------|
| `mcp_version` | `latest` | Package version. Use `latest` for the newest PyPI release or pin to a specific version (e.g., `0.12.1`). Must be a pinned version for offline installs. |
| `mcp_python_executable` | `/usr/bin/python3.11` | Python executable used to create the virtual environment. |
| `mcp_python_packages` | `[python3.11]` | OS packages installed before creating the virtual environment. Add `python3.11-pip` for Amazon Linux 2023. |
| `mcp_install_dir` | `/opt/itential-mcp` | Root installation directory. |
| `mcp_venv_dir` | `/opt/itential-mcp/venv` | Python virtual environment path. |

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `mcp_transport` | `sse` | Transport protocol. Valid values: `sse`, `http`. |
| `mcp_host` | `0.0.0.0` | IP address the server listens on. |
| `mcp_port` | `8000` | Port the server listens on. |
| `mcp_log_level` | `INFO` | Log verbosity. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `NONE`. |
| `mcp_response_format` | `json` | Response serialization format. Valid values: `json`, `toon`. |
| `mcp_include_tags` | `""` | Comma-separated list of tool tags to include. Empty includes all tools. |
| `mcp_exclude_tags` | `experimental,beta` | Comma-separated list of tool tags to exclude. |
| `mcp_keepalive_interval` | `300` | Seconds between keepalive requests to the Platform. Set to `0` to disable. |
| `mcp_conf_dir` | `/etc/itential-mcp` | Directory for configuration files. |
| `mcp_log_dir` | `/var/log/itential-mcp` | Directory for log files. |
| `mcp_owner` | `itential-mcp` | System user the service runs as. |
| `mcp_group` | `itential-mcp` | System group the service runs as. |

### Platform Connection

| Variable | Default | Description |
|----------|---------|-------------|
| `mcp_platform_host` | `localhost` | Hostname or IP of the Itential Platform server. |
| `mcp_platform_port` | `3000` | Platform API port. Default `3000` (HTTP). Use `3443` for HTTPS. |
| `mcp_platform_user` | `admin` | Username for basic authentication. Ignored when OAuth credentials are set. |
| `mcp_platform_password` | `admin` | Password for basic authentication. |
| `mcp_platform_client_id` | `""` | OAuth client ID. When set, OAuth is used instead of basic auth. |
| `mcp_platform_client_secret` | `""` | OAuth client secret. |
| `mcp_platform_timeout` | `30` | Request timeout in seconds. |

**&#9432; Note:** All credentials are written to `/etc/itential-mcp/itential-mcp.env`
with mode `0600`. They are never written to `mcp.conf`. Using Ansible Vault for
credential values is strongly recommended.

### TLS Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `mcp_platform_tls` | `false` | Set to `true` when the Platform API is served over HTTPS. |
| `mcp_platform_disable_verify` | `false` | Set to `true` to skip TLS certificate verification. Use only in development environments. |
| `mcp_platform_ca_bundle` | `""` | Path to a CA certificate bundle on the MCP server. Required when the Platform uses a certificate signed by a private CA. See [TLS Configuration](#tls-configuration). |

### Offline Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `offline_install_enabled` | `false` | Set to `true` to install from a pre-staged package bundle instead of PyPI. |
| `offline_target_node_root` | `/var/tmp` | Directory on the target server where the package bundle is staged. |
| `offline_control_node_root` | `{{ playbook_dir }}/files` | Directory on the control node containing the `itential-mcp-packages/` bundle. |

### Certify Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `mcp_certify_report_dir_remote` | `/tmp/itential-mcp-certify` | Directory on the target server where the report is generated. |
| `mcp_certify_report_dir_local` | `{{ playbook_dir }}/certify-reports` | Directory on the control node where the report is fetched. |

---

## Example Inventories

Three example inventories are provided in `example_inventories/mcp/`:

| File | Use Case |
|------|----------|
| `mcp_default_passwords.yaml` | Standard install with minimum required variables |
| `mcp_override_default_passwords.yaml` | All variables explicitly set |
| `mcp_offline.yaml` | Air-gapped / offline install |

---

## Offline Installation

For environments without internet access, pre-stage the package bundle on a
Linux host matching the target OS and Python version before running the playbook.

**&#9432; Important:** Run `pip download` on a Linux host, not macOS or Windows.
macOS does not resolve Linux-specific conditional dependencies correctly, resulting
in an incomplete bundle.

Stage the bundle on a Linux host with internet access:

```bash
pip download 'itential-mcp==0.12.1' 'fastmcp>=3.0,<3.3' \
  -d /path/to/playbook/files/itential-mcp-packages/
```

Then set the following in your inventory:

```yaml
offline_install_enabled: true
mcp_version: "0.12.1"
offline_control_node_root: /path/to/playbook/files
```

Run the install playbook as normal. The role copies the bundle to the target
server and installs from it using `--no-index`.

---

## TLS Configuration

When connecting to an Itential Platform that uses HTTPS, configure the following:

### Platform with a Public CA Certificate

```yaml
mcp_platform_tls: true
mcp_platform_port: 3443
```

No additional steps required. The server's Python trust store (certifi) trusts
public certificate authorities by default.

### Platform with a Private CA Certificate

The MCP server's Python HTTP client uses `certifi` for certificate validation, not
the OS trust store. After installing the CA cert to the OS, the CA bundle path must
be provided so Python uses it.

1. Copy the CA certificate to the MCP server:

```bash
scp ca.crt user@mcp-server:/tmp/itential-ca.crt
ssh user@mcp-server "sudo cp /tmp/itential-ca.crt /etc/pki/ca-trust/source/anchors/itential-ca.crt && sudo update-ca-trust"
```

2. Set the following in your inventory:

```yaml
mcp_platform_tls: true
mcp_platform_port: 3443
mcp_platform_ca_bundle: /etc/pki/tls/certs/ca-bundle.crt
```

The role writes `SSL_CERT_FILE={{ mcp_platform_ca_bundle }}` to the service
environment file, directing Python to use the system CA bundle which now includes
your private CA.

---

## High Availability Platform

The MCP server connects to a single `mcp_platform_host`. In a Platform HA
deployment, point `mcp_platform_host` at the load balancer VIP or hostname. The
load balancer handles failover — no additional role configuration is required.

```yaml
mcp_platform_host: platform-lb.example.com
mcp_platform_port: 3443
mcp_platform_tls: true
```

---

## Upgrading

To upgrade the `itential-mcp` package to the latest version, change
`mcp_version: latest` in your inventory and re-run the install playbook:

```bash
ansible-playbook itential.mcp.mcp -i your_inventory.yaml
```

The role detects the installed version, upgrades the package if a newer version
is available, and restarts the service. Run the certify playbook afterward to
confirm the upgrade was successful.

To pin to a specific version, set `mcp_version: "0.12.1"`. The role will
install that exact version and leave it unchanged on subsequent runs.
