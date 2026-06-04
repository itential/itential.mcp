# itential.mcp — Codebase Reference

**Version:** 0.1.0 | **Role:** `mcp` | **Updated:** 2026-05-18

---

## Purpose and Architecture

`itential.mcp` is an Ansible collection that installs and manages the
[itential-mcp](https://github.com/itential/itential-mcp) Python package as a
`systemd` service on RHEL-family and Amazon Linux VMs. It is the deployment
counterpart to the `itential.deployer` collection — deployer installs Platform,
`itential.mcp` installs the MCP server that connects AI agents to it.

**Primary data flow:**

```
AI client (Claude Desktop, Claude Code, etc.)
  ↓  MCP protocol (SSE or HTTP transport)
itential-mcp service (this role installs and manages this)
  ↓  ipsdk / HTTPS
Itential Platform
  ↓
Network devices
```

**What the role does, in order:**

1. Validate all inventory variables (assertions, fail fast)
2. Install `python3.11` via `dnf`
3. Create `/opt/itential-mcp/venv` and `pip install itential-mcp`
4. Create `itential-mcp` system user/group
5. Write `/etc/itential-mcp/mcp.conf` (non-sensitive server and platform config)
6. Write `/etc/itential-mcp/itential-mcp.env` (credentials, config path, CA bundle)
7. Install `/etc/systemd/system/itential-mcp.service`
8. Enable and start the service via handler
9. Assert `ActiveState == active`

---

## Collection Structure

```
itential.mcp/
├── galaxy.yml                          Collection metadata
├── meta/runtime.yml                    Requires ansible >= 2.14
├── README.md                           User-facing documentation
├── CLAUDE.md                           This file
├── playbooks/
│   ├── mcp.yml                         Install and configure
│   ├── verify_mcp.yml                  Pre-install checks
│   └── certify_mcp.yml                 Post-install validation + report
├── roles/mcp/
│   ├── defaults/main/
│   │   ├── main.yml                    All role variables and defaults
│   │   └── offline.yml                 Offline install variables
│   ├── tasks/
│   │   ├── main.yml                    Entry point and flow control
│   │   ├── validate-vars.yml           Assertions (transport, port, offline version)
│   │   ├── install-python.yml          dnf install python3.11
│   │   ├── install-mcp.yml             pip install (online)
│   │   ├── install-mcp-offline.yml     Copy bundle + pip install (offline)
│   │   ├── configure-mcp.yml           User, dirs, mcp.conf, env file, systemd unit
│   │   ├── verify-mcp.yml              Pre-install checks
│   │   └── certify-mcp.yml             Post-install validation + report generation
│   ├── handlers/main.yml               restart itential-mcp (systemd)
│   └── templates/
│       ├── mcp.conf.j2                 [server] + [platform] INI config
│       ├── itential-mcp.env.j2         Credentials environment file
│       ├── itential-mcp.service.j2     systemd unit
│       └── certify-report.j2           Markdown certification report
├── example_inventories/mcp/
│   ├── mcp_default_passwords.yaml      Minimal required variables
│   ├── mcp_override_default_passwords.yaml  All variables explicit
│   └── mcp_offline.yaml                Offline install variant
└── files/
    └── itential-mcp-packages/          Offline wheel bundle (not committed)
```

---

## Key Design Decisions

### Credentials in the Environment File, Not mcp.conf

`mcp.conf` has mode `0640` (group-readable). Credentials — platform user/password
or OAuth client_id/secret — go in `/etc/itential-mcp/itential-mcp.env` with mode
`0600` (owner-only). This means non-sensitive config can be reviewed without
exposing secrets.

The env file also sets `ITENTIAL_MCP_CONFIG` pointing to the conf file. This is
required because of an argparse bug in itential-mcp (see Known Issues).

### fastmcp Version Pin

`install-mcp.yml` and `install-mcp-offline.yml` both pin `fastmcp>=3.0,<3.3`
alongside the `itential-mcp` package. `fastmcp` 3.3.0 broke the API that
itential-mcp 0.12.1 relies on. The pin must stay until itential-mcp releases a
version that supports fastmcp 3.3.x.

### stdio Transport Explicitly Excluded

`validate-vars.yml` rejects `mcp_transport=stdio` with a clear error. stdio is
incompatible with systemd service management — systemd sets `StandardInput=null`
which delivers EOF to stdin immediately, causing the stdio MCP server to exit
cleanly (exit code 0). The symptom is a service that starts and stops in ~2
seconds with no error in the journal.

### Python Uses certifi, Not the OS Trust Store

The `httpx`-based HTTP client in itential-mcp uses the `certifi` CA bundle, not
the OS trust store, even after `update-ca-trust`. `mcp_platform_ca_bundle` writes
`SSL_CERT_FILE={{ path }}` to the env file, directing Python to use the system
bundle which includes any private CAs added via `update-ca-trust`.

### Handler + state:started for Service Idempotency

The `configure-mcp.yml` task uses `state: started` (not just `enabled: true`) on
the systemd module. This ensures the service starts on the first run regardless of
whether any tasks reported `changed`. The handler uses `state: restarted` and fires
when config files change.

The `flush_handlers` meta task before the final assertion ensures the handler fires
(and the service restarts) before we check `ActiveState`.

---

## Known Issues

### 1. itential-mcp argparse Drops `--config` Flag

**What happens:** When `itential-mcp --config /path/to/mcp.conf run` is called,
the argparse subparser for the `run` subcommand inherits `--config` from the
parent parser and overwrites `args.config = None`. The `ITENTIAL_MCP_CONFIG`
environment variable is therefore never set, and `config.get()` falls back to all
defaults — including `transport = stdio`.

**Symptom:** Service starts in stdio mode. With `StandardInput=null`, stdin returns
EOF and the server exits cleanly in ~2 seconds (status=0). No error in the journal.

**Workaround:** The env file template writes `ITENTIAL_MCP_CONFIG={{ mcp_conf_file }}`.
With this env var set, `config.get()` reads the config file without relying on the
CLI arg.

**File:** `templates/itential-mcp.env.j2`

---

### 2. fastmcp 3.3.x Incompatible with itential-mcp 0.12.1

**What happens:** `from fastmcp import FastMCP` raises `ImportError` with
fastmcp 3.3.x. The `fastmcp.server.middleware.*` modules that itential-mcp imports
were also removed in 3.3.0.

**Workaround:** `fastmcp>=3.0,<3.3` pinned in both `install-mcp.yml` and
`install-mcp-offline.yml`.

**Action:** Monitor itential-mcp releases. Remove the pin once a compatible version
ships.

---

### 3. Env Vars Do Not Override Config File Values

**What happens:** Adding `ITENTIAL_MCP_SERVER_LOG_LEVEL=DEBUG` to the systemd
`EnvironmentFile` does not override `log_level = INFO` in `mcp.conf`. The INI
config file source has higher priority than env vars when `ITENTIAL_MCP_CONFIG`
is set. The documented precedence (env vars > config file) does not hold in
practice.

**Implication:** All server settings must be managed through the config file.
Do not rely on `EnvironmentFile` entries to override config file values. Only
credentials, the config file path pointer, and `SSL_CERT_FILE` belong in the
env file.

**Status:** Not yet reported upstream.

---

### 4. itential-mcp 0.12.0 Incompatible with fastmcp 3.x

**What happens:** 0.12.0 passes `include_tags`/`exclude_tags` as kwargs to
`FastMCP()`. These were removed in fastmcp 3.x. Service crashes on startup with:
```
TypeError: FastMCP() no longer accepts `include_tags`.
```

The fastmcp pin `>=3.0,<3.3` therefore requires `itential-mcp >= 0.12.1`.

---

### 5. Offline Bundle Must Be Generated on Linux

Running `pip download --platform manylinux_2_17_x86_64` on macOS does not resolve
Linux-specific or Python-version-specific conditional dependencies (e.g.,
`SecretStorage`, `backports.tarfile`). The resulting bundle is incomplete.

Generate the offline bundle on a Linux host matching the target OS and Python
version, then copy it to the control node. The bundle in `files/itential-mcp-packages/`
was generated on Amazon Linux 2023 with Python 3.11.

---

### 6. certify Tool Count Does Not Reflect Tag Filtering

`itential-mcp tools` lists all registered tools regardless of `include_tags` /
`exclude_tags` in the config. The certify `Tools available` metric reflects the
total registered tool count, not the actively filtered set exposed to clients.

---

## Variable Reference (Quick Reference)

Key variables and their non-obvious behaviors:

| Variable | Default | Note |
|----------|---------|------|
| `mcp_version` | `latest` | `latest` uses `pip state: latest`; pinned version uses `state: present` |
| `mcp_transport` | `sse` | `stdio` is rejected by validation |
| `mcp_platform_port` | `3000` | Itential Platform HTTP default. Use `3443` for HTTPS. |
| `mcp_platform_tls` | `false` | Maps to `disable_tls = True/False` in mcp.conf (inverted) |
| `mcp_platform_ca_bundle` | `""` | When set, writes `SSL_CERT_FILE` to env file |
| `mcp_platform_client_id` | `""` | When set, OAuth creds replace user/password in env file |
| `mcp_keepalive_interval` | `300` | Set to `0` to disable keepalive entirely |
| `offline_install_enabled` | `false` | Requires `mcp_version` to be pinned (not `latest`) |

### mcp_platform_tls Inversion

The inventory variable `mcp_platform_tls: true` means "TLS is enabled". But the
mcp.conf setting is `disable_tls`. The template inverts it:

```jinja2
disable_tls = {{ (not mcp_platform_tls | bool) | lower }}
```

---

## Files on the Target Server

```
/opt/itential-mcp/
└── venv/                   Python virtual environment (root-owned)

/etc/itential-mcp/
├── mcp.conf                Server and platform config (mode 0640, itential-mcp:itential-mcp)
└── itential-mcp.env        Credentials + config path (mode 0600, itential-mcp:itential-mcp)

/var/log/itential-mcp/      Log directory (itential-mcp:itential-mcp, mode 0755)

/etc/systemd/system/
└── itential-mcp.service    systemd unit (root, mode 0644)
```

---

## Testing Notes

A full test record is maintained in `testing.md` (not committed — personal notes).
Key findings relevant to future work:

- Tested on: Rocky Linux 9, Amazon Linux 2023
- All transport modes (SSE, HTTP), all auth methods (basic auth, OAuth), TLS with
  public and private CAs have been validated
- Offline install tested on Amazon Linux 2023; bundle generated on that same host
- End-to-end test: Claude Desktop connected via local stdio install, called
  `get_health` and `get_workflows` successfully against a live Platform

---

## Entry Points

When working on this collection:

1. Start with `roles/mcp/defaults/main/main.yml` — all variables and their defaults
2. Read `roles/mcp/tasks/main.yml` — the task flow is defined here
3. Read `roles/mcp/templates/itential-mcp.env.j2` — this is where the argparse
   workaround lives (`ITENTIAL_MCP_CONFIG`)
4. Read `Known Issues` above before making any changes to startup behavior

When debugging a service that exits immediately:
- Check `journalctl -u itential-mcp --no-pager -n 30`
- If you see only an authlib deprecation warning and "Deactivated successfully",
  the stdio transport is being used — the `ITENTIAL_MCP_CONFIG` env var is not set
- If you see "TypeError: FastMCP() no longer accepts", the fastmcp version pin
  has been lost and 3.3.x was installed
