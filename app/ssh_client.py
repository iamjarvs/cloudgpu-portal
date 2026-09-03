"""SSH automation against the demo lab's bare-metal fleet.

Two things live here, both driven through the same jump host:

1. Silently installing/uninstalling a fake "training job monitor" webpage on
   every server in a real environment — invisible to the customer persona,
   purely a prop for Adam's own live demos. Best-effort: never raises past
   its public functions, only logs, and never blocks or fails the
   provisioning/delete flow it's attached to.
2. The customer-facing "Test Connectivity" action, which genuinely needs to
   surface real errors (unlike #1, this is a deliberate, on-demand action the
   customer persona triggers and watches the result of).

Reachability quirk this module exists to work around: the individual
`hgx-podNN-suX-hYY` hosts are only reachable via **bash aliases** defined in
the jump host's `~/.bash_aliases` (e.g. `alias hgx-pod00-su0-h00='ssh -o
StrictHostKeyChecking=no root@192.168.16.2'`), sourced only in *interactive*
shells. A plain non-interactive `ssh jumphost 'ssh hgx-pod00-su0-h00 ...'`
never sees that alias and fails with a DNS error — hostnames like that
aren't real hostnames at all. The fix is to resolve the alias table once
(via `bash -i -c alias`, which forces `.bashrc`/`.bash_aliases` to load) and
then connect directly to the resolved IP for every subsequent hop, bypassing
alias expansion entirely.

Host keys on the target VMs are expected to change over time (they're
libvirt-backed simulated hosts that get recreated) — StrictHostKeyChecking
is disabled for the nested hop, matching how this lab is actually operated
(see the alias definitions themselves, which already do this).
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import asyncssh

from app import settings_store
from app.security import SecretBox

logger = logging.getLogger("ssh")

_ASSET_DIR = Path(__file__).resolve().parent / "ssh_assets"
_HEREDOC_DELIM = "__HELIOSGRID_EOF__"
_DEMO_UNIT = "heliosgrid-demo"
_DEMO_DIR = "/opt/heliosgrid-demo"
_ALIAS_RE = re.compile(r"alias (hgx-\S+)='ssh .*?root@([0-9.]+)'")
_SU_HOST_RE = re.compile(r"su(\d+)-h(\d+)")

_UNINSTALL_SCRIPT = (
    f"systemctl stop {_DEMO_UNIT} >/dev/null 2>&1 || true\n"
    f"rm -rf {_DEMO_DIR}\n"
)


def parse_su_host(server_name: str) -> tuple[int, int] | None:
    m = _SU_HOST_RE.search(server_name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _install_script(hostname: str, port: int) -> str:
    page = (_ASSET_DIR / "training_viz.html").read_text().replace("{{HOSTNAME}}", hostname)
    return (
        f"mkdir -p {_DEMO_DIR}\n"
        f"cat > {_DEMO_DIR}/index.html << '{_HEREDOC_DELIM}'\n"
        f"{page}\n"
        f"{_HEREDOC_DELIM}\n"
        f"systemctl stop {_DEMO_UNIT} >/dev/null 2>&1 || true\n"
        f"systemd-run --unit={_DEMO_UNIT} --collect --working-directory={_DEMO_DIR} "
        f"/usr/bin/python3 -m http.server {port}\n"
    )


class SSHNotConfiguredError(Exception):
    pass


class ConnectivityTestError(Exception):
    pass


async def _connect_jump(secret_box: SecretBox) -> asyncssh.SSHClientConnection:
    settings = settings_store.get_settings()
    if not settings.ssh_configured:
        raise SSHNotConfiguredError("SSH jump host is not configured yet — set it up in /ops.")
    password = secret_box.decrypt(settings.ssh_jump_password_encrypted)
    return await asyncssh.connect(
        settings.ssh_jump_host,
        port=settings.ssh_jump_port,
        username=settings.ssh_jump_username,
        password=password,
        known_hosts=None,
    )


async def resolve_aliases(conn: asyncssh.SSHClientConnection) -> dict[str, str]:
    result = await conn.run("bash -i -c alias 2>/dev/null", check=False)
    mapping: dict[str, str] = {}
    for line in result.stdout.splitlines():
        m = _ALIAS_RE.match(line)
        if m:
            mapping[m.group(1)] = m.group(2)
    return mapping


async def _run_on_ip(
    conn: asyncssh.SSHClientConnection, ip: str, script: str, timeout: float = 25
) -> asyncssh.SSHCompletedProcess:
    coro = conn.run(
        f'ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10 root@{ip} "bash -s"',
        input=script,
        check=False,
    )
    return await asyncio.wait_for(coro, timeout=timeout)


async def install_demo_app(secret_box: SecretBox, servers: list[dict]) -> None:
    """Best-effort. Logs and moves on — never raises, never blocks provisioning."""
    settings = settings_store.get_settings()
    if not settings.ssh_configured:
        logger.info("SSH not configured — skipping demo webpage install")
        return
    try:
        async with await _connect_jump(secret_box) as conn:
            aliases = await resolve_aliases(conn)
            for server in servers:
                name = server["name"]
                ip = aliases.get(name)
                if not ip:
                    logger.warning("No SSH alias found for %s — skipping demo webpage install", name)
                    continue
                try:
                    result = await _run_on_ip(conn, ip, _install_script(name, settings.demo_app_port))
                    if result.exit_status == 0:
                        logger.info("Installed demo training-viz webpage on %s (port %s)", name, settings.demo_app_port)
                    else:
                        logger.warning(
                            "Demo webpage install on %s exited %s: %s", name, result.exit_status, result.stderr[-500:]
                        )
                except Exception:
                    logger.exception("Demo webpage install failed on %s", name)
    except Exception:
        logger.exception("Could not reach SSH jump host for demo webpage install")


async def uninstall_demo_app(secret_box: SecretBox, servers: list[dict]) -> None:
    """Best-effort. Logs and moves on — never raises, never blocks deletion."""
    settings = settings_store.get_settings()
    if not settings.ssh_configured:
        return
    try:
        async with await _connect_jump(secret_box) as conn:
            aliases = await resolve_aliases(conn)
            for server in servers:
                name = server["name"]
                ip = aliases.get(name)
                if not ip:
                    continue
                try:
                    await _run_on_ip(conn, ip, _UNINSTALL_SCRIPT)
                    logger.info("Removed demo training-viz webpage from %s", name)
                except Exception:
                    logger.exception("Demo webpage uninstall failed on %s", name)
    except Exception:
        logger.exception("Could not reach SSH jump host for demo webpage uninstall")


async def test_connectivity(secret_box: SecretBox, source_server: dict, target_servers: list[dict]) -> dict:
    """Customer-facing — raises ConnectivityTestError with a clear message on failure
    rather than swallowing it, unlike the install/uninstall helpers above."""
    settings = settings_store.get_settings()
    if not settings.ssh_configured:
        raise ConnectivityTestError("SSH access is not configured for this Neo Cloud yet.")

    source_name = source_server["name"]
    if parse_su_host(source_name) is None:
        raise ConnectivityTestError(f"Could not determine SU/host number from server name '{source_name}'.")

    targets = []
    for t in target_servers:
        su_host = parse_su_host(t["name"])
        if su_host is not None:
            targets.append((t["name"], su_host))

    if not targets:
        return {
            "server_name": source_name,
            "target_count": 0,
            "output": "Only one server in this environment — no peers to test connectivity against.",
        }

    try:
        async with await _connect_jump(secret_box) as conn:
            aliases = await resolve_aliases(conn)
    except Exception as exc:
        raise ConnectivityTestError(f"Could not reach the SSH jump host: {exc}") from exc

    source_ip = aliases.get(source_name)
    if not source_ip:
        raise ConnectivityTestError(f"No SSH alias found for '{source_name}' on the jump host.")

    script_lines = []
    for target_name, (su, host) in targets:
        script_lines.append(f'echo "=== {target_name} (SU {su}, Host {host}) ==="')
        script_lines.append(f"./cluster-ping.sh {su} {host}")
        script_lines.append("echo")
    script = "\n".join(script_lines) + "\n"

    try:
        async with await _connect_jump(secret_box) as conn:
            result = await _run_on_ip(conn, source_ip, script, timeout=15 * len(targets) + 15)
    except Exception as exc:
        raise ConnectivityTestError(f"SSH to '{source_name}' failed: {exc}") from exc

    return {
        "server_name": source_name,
        "target_count": len(targets),
        "output": result.stdout or result.stderr or "(no output)",
        "exit_status": result.exit_status,
    }
