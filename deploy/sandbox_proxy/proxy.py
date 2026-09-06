#!/usr/bin/env python3
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Zero-dependency egress filtering forward proxy for AI sandbox containers."""

import asyncio
import fnmatch
import logging
import os
import re
import signal
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sandbox-egress-proxy")

CONNECT_PATTERN = re.compile(r"^CONNECT\s+([a-zA-Z0-9.-]+):(\d+)\s+HTTP/1\.[01]$", re.IGNORECASE)
UPSTREAM_CONNECT_TIMEOUT = 10.0


def load_allowlist(config_path: Path | None = None) -> list[tuple[str, int]]:
    """Load allowed host patterns and ports from an allowlist configuration file.

    Fails closed (returns empty list) if the file is missing, unreadable, or empty.
    Single Source of Truth: deploy/sandbox_proxy/allowlist.conf.
    """
    if config_path is None:
        config_path = Path(__file__).resolve().parent / "allowlist.conf"

    if not config_path.is_file():
        logger.error("Allowlist file not found at %s. FAILING CLOSED (all egress blocked).", config_path)
        return []

    rules: list[tuple[str, int]] = []
    try:
        content = config_path.read_text(encoding="utf-8")
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                host_part, port_str = line.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 443
            else:
                host_part, port = line, 443
            rules.append((host_part.lower(), port))
        if not rules:
            logger.error("Allowlist at %s contains no active rules. FAILING CLOSED.", config_path)
            return []
        logger.info("Loaded %d egress allowlist rules from %s", len(rules), config_path)
    except OSError as err:
        logger.error("Failed to read allowlist file %s: %s. FAILING CLOSED.", config_path, err)
        return []

    return rules


def is_destination_allowed(host: str, port: int, rules: list[tuple[str, int]]) -> bool:
    """Check if destination host and port match any allowlist rule."""
    normalized_host = host.lower().strip()
    for pattern, allowed_port in rules:
        if port != allowed_port:
            continue
        if pattern == normalized_host:
            return True
        if pattern.startswith("*."):
            base_domain = pattern[2:]
            if normalized_host == base_domain or normalized_host.endswith("." + base_domain):
                return True
        elif fnmatch.fnmatch(normalized_host, pattern):
            return True
    return False


async def pipe_streams(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Relay data bidirectionally between client and remote sockets."""
    try:
        while not reader.at_eof():
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except (OSError, asyncio.CancelledError):
            pass


async def _handle_connect(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    target_host: str,
    target_port: int,
    rules: list[tuple[str, int]],
    peer_name: object,
) -> None:
    """Handle CONNECT method tunneling to authorized destinations."""
    if not is_destination_allowed(target_host, target_port, rules):
        logger.warning("BLOCKED CONNECT attempt to %s:%d from %s", target_host, target_port, peer_name)
        deny_response = (
            b"HTTP/1.1 403 Forbidden\r\n"
            b"Content-Type: text/plain\r\n"
            b"Connection: close\r\n\r\n"
            b"403 Forbidden: Destination not permitted by AI sandbox egress policy\r\n"
        )
        client_writer.write(deny_response)
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return

    logger.info("ALLOWED CONNECT tunnel to %s:%d from %s", target_host, target_port, peer_name)
    try:
        remote_reader, remote_writer = await asyncio.wait_for(
            asyncio.open_connection(target_host, target_port),
            timeout=UPSTREAM_CONNECT_TIMEOUT,
        )
    except (TimeoutError, asyncio.TimeoutError):
        logger.error("Timeout connecting to upstream %s:%d", target_host, target_port)
        client_writer.write(b"HTTP/1.1 504 Gateway Timeout\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return
    except OSError as err:
        logger.error("Failed to connect to %s:%d: %s", target_host, target_port, err)
        client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return

    client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await client_writer.drain()

    pipe1 = asyncio.create_task(pipe_streams(client_reader, remote_writer))
    pipe2 = asyncio.create_task(pipe_streams(remote_reader, client_writer))
    await asyncio.gather(pipe1, pipe2, return_exceptions=True)


async def _handle_http(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    method: str,
    target: str,
    headers: list[str],
    rules: list[tuple[str, int]],
    peer_name: object,
) -> None:
    """Handle standard HTTP methods (GET, POST) to authorized destinations."""
    host_header = ""
    for h in headers:
        if h.lower().startswith("host:"):
            host_header = h.split(":", 1)[1].strip()
            break

    host_to_check = host_header or target
    port_to_check = 80
    if ":" in host_to_check:
        host_to_check, port_str = host_to_check.rsplit(":", 1)
        try:
            port_to_check = int(port_str)
        except ValueError:
            port_to_check = 80

    if not is_destination_allowed(host_to_check, port_to_check, rules):
        logger.warning("BLOCKED HTTP %s request to %s:%d from %s", method, host_to_check, port_to_check, peer_name)
        deny_response = (
            b"HTTP/1.1 403 Forbidden\r\n"
            b"Content-Type: text/plain\r\n"
            b"Connection: close\r\n\r\n"
            b"403 Forbidden: Host not permitted by AI sandbox egress policy\r\n"
        )
        client_writer.write(deny_response)
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return

    logger.info("ALLOWED HTTP %s request to %s:%d from %s", method, host_to_check, port_to_check, peer_name)
    try:
        remote_reader, remote_writer = await asyncio.wait_for(
            asyncio.open_connection(host_to_check, port_to_check),
            timeout=UPSTREAM_CONNECT_TIMEOUT,
        )
    except (TimeoutError, asyncio.TimeoutError):
        logger.error("Timeout connecting to upstream HTTP %s:%d", host_to_check, port_to_check)
        client_writer.write(b"HTTP/1.1 504 Gateway Timeout\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return
    except OSError as err:
        logger.error("Failed to connect to %s:%d: %s", host_to_check, port_to_check, err)
        client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return

    remote_writer.write(f"{method} {target} HTTP/1.1\r\n".encode())
    for h in headers:
        remote_writer.write(f"{h}\r\n".encode())
    remote_writer.write(b"\r\n")
    await remote_writer.drain()

    pipe1 = asyncio.create_task(pipe_streams(client_reader, remote_writer))
    pipe2 = asyncio.create_task(pipe_streams(remote_reader, client_writer))
    await asyncio.gather(pipe1, pipe2, return_exceptions=True)


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    rules: list[tuple[str, int]],
) -> None:
    """Handle an incoming client proxy connection (CONNECT or standard HTTP)."""
    peer_name = client_writer.get_extra_info("peername")
    try:
        request_line_bytes = await client_reader.readline()
        if not request_line_bytes:
            client_writer.close()
            await client_writer.wait_closed()
            return

        request_line = request_line_bytes.decode("utf-8", errors="replace").strip()
        connect_match = CONNECT_PATTERN.match(request_line)

        headers: list[str] = []
        while True:
            header_line = await client_reader.readline()
            if not header_line or header_line in (b"\r\n", b"\n"):
                break
            headers.append(header_line.decode("utf-8", errors="replace").strip())

        if connect_match:
            target_host = connect_match.group(1).lower()
            try:
                target_port = int(connect_match.group(2))
            except ValueError:
                target_port = 0
            await _handle_connect(client_reader, client_writer, target_host, target_port, rules, peer_name)
        else:
            parts = request_line.split()
            if len(parts) < 2:
                client_writer.close()
                await client_writer.wait_closed()
                return
            await _handle_http(client_reader, client_writer, parts[0].upper(), parts[1], headers, rules, peer_name)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Exception handling client connection: %s", exc)
    finally:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except (OSError, asyncio.CancelledError):
            pass


async def main() -> None:
    """Parse configuration and start proxy server."""
    port_str = os.environ.get("PROXY_PORT", "3128")
    try:
        listen_port = int(port_str)
    except ValueError:
        listen_port = 3128

    config_env = os.environ.get("ALLOWLIST_CONFIG")
    config_path = Path(config_env) if config_env else None
    rules = load_allowlist(config_path)

    logger.info("Starting sandbox egress proxy on 0.0.0.0:%d with %d rules...", listen_port, len(rules))

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, rules),
        host="0.0.0.0",
        port=listen_port,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal() -> None:
        logger.info("Received termination signal, stopping proxy...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, RuntimeError):
            pass

    async with server:
        serve_task = asyncio.create_task(server.serve_forever())
        wait_stop = asyncio.create_task(stop_event.wait())
        done, _ = await asyncio.wait([serve_task, wait_stop], return_when=asyncio.FIRST_COMPLETED)
        if wait_stop in done:
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
