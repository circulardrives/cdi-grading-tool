#
# Copyright (c) 2026 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

DEFAULT_CDI_PORT = 8844
MAX_HOSTS_PER_SCAN = 256
MAX_SUBNETS_PER_REQUEST = 4
DISCOVER_COOLDOWN_SECONDS = 10

PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
)


class DiscoveryError(ValueError):
    """Raised when discovery parameters or timing constraints are invalid."""


def parse_subnet(value: str) -> ipaddress.IPv4Network:
    """Parse a CIDR subnet string into an IPv4 network."""
    try:
        network = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError as exc:
        raise DiscoveryError(f"Invalid subnet: {value}") from exc

    if not isinstance(network, ipaddress.IPv4Network):
        raise DiscoveryError(f"Only IPv4 subnets are supported: {value}")

    if network.num_addresses > MAX_HOSTS_PER_SCAN:
        raise DiscoveryError(
            f"Subnet {value} is too large ({network.num_addresses} addresses). "
            f"Maximum allowed is {MAX_HOSTS_PER_SCAN} (/24 or smaller)."
        )

    if not _subnet_is_allowed(network):
        raise DiscoveryError(
            f"Subnet {value} is not allowed. Discovery is limited to private/link-local ranges."
        )

    return network


def _subnet_is_allowed(network: ipaddress.IPv4Network) -> bool:
    return any(network.subnet_of(allowed) for allowed in PRIVATE_NETWORKS)


def get_local_ipv4_addresses() -> list[str]:
    """Collect non-loopback IPv4 addresses from the host running the API."""
    addresses: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            addresses.add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            if not addr.startswith("127."):
                addresses.add(addr)
    except OSError:
        pass

    return sorted(addresses)


def derive_local_subnets(prefix_len: int = 24) -> list[str]:
    """Derive /24 (by default) subnets from local interface addresses."""
    subnets: list[str] = []
    for addr in get_local_ipv4_addresses():
        network = ipaddress.ip_network(f"{addr}/{prefix_len}", strict=False)
        subnet = str(network)
        if subnet not in subnets:
            subnets.append(subnet)
    return subnets


def resolve_subnets(subnet: str | None, subnets: list[str] | None) -> list[str]:
    """Resolve explicit subnet(s) or fall back to local interface subnets."""
    explicit: list[str] = []
    if subnet:
        explicit.append(subnet.strip())
    if subnets:
        explicit.extend(item.strip() for item in subnets if item.strip())

    if explicit:
        if len(explicit) > MAX_SUBNETS_PER_REQUEST:
            raise DiscoveryError(
                f"At most {MAX_SUBNETS_PER_REQUEST} subnets can be scanned per request."
            )
        return explicit

    local = derive_local_subnets()
    if not local:
        raise DiscoveryError(
            "Could not determine a local subnet. Provide subnet explicitly, e.g. 192.168.0.0/24."
        )
    return local[:MAX_SUBNETS_PER_REQUEST]


def iter_host_addresses(network: ipaddress.IPv4Network) -> list[str]:
    """Return host addresses to probe (excluding network/broadcast for legacy networks)."""
    if network.num_addresses <= 2:
        return [str(network.network_address)]

    hosts = [str(host) for host in network.hosts()]
    return hosts[:MAX_HOSTS_PER_SCAN]


def normalize_machine_address(value: str) -> tuple[str, int | None]:
    """Return `(ip, port)` parsed from a machine address or hostname field."""
    cleaned = value.strip()
    if not cleaned:
        return "", None

    if ":" in cleaned and cleaned.count(":") == 1:
        host, _, port_text = cleaned.rpartition(":")
        try:
            return host.strip(), int(port_text)
        except ValueError:
            return cleaned, None

    return cleaned, None


def is_already_registered(
    ip: str,
    port: int,
    registered_machines: list[dict[str, Any]],
) -> bool:
    """Return True when the discovered endpoint matches an existing fleet host."""
    target = f"{ip}:{port}"
    for machine in registered_machines:
        address_ip, address_port = normalize_machine_address(machine.get("address", ""))
        if address_ip == ip and (address_port is None or address_port == port):
            return True

        hostname = str(machine.get("hostname", "")).strip()
        if hostname in {ip, target}:
            return True

    return False


def is_port_open(ip: str, port: int, timeout_seconds: float) -> bool:
    """Return True when a TCP port accepts connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        try:
            return sock.connect_ex((ip, port)) == 0
        except OSError:
            return False


def reverse_hostname(ip: str) -> str | None:
    """Best-effort reverse DNS lookup for a discovered host."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def probe_cdi_health(
    ip: str,
    port: int,
    *,
    probe_token: str | None,
    timeout_seconds: float,
) -> dict[str, Any] | None:
    """Probe a remote CDI Health API health endpoint."""
    url = f"http://{ip}:{port}/api/v1/health"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if probe_token:
        request.add_header("X-API-Token", probe_token)

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    return payload if isinstance(payload, dict) else None


def discover_hosts(
    *,
    subnet: str | None = None,
    subnets: list[str] | None = None,
    port: int = DEFAULT_CDI_PORT,
    timeout_seconds: float = 1.5,
    probe_token: str | None = None,
    registered_machines: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Scan private LAN subnet(s) for CDI Health API instances on the given port.

    Discovery runs from the machine hosting this API process (technician laptop or jump host).
    """
    started = time.monotonic()
    subnet_values = resolve_subnets(subnet, subnets)
    networks = [parse_subnet(value) for value in subnet_values]

    hosts: list[str] = []
    seen_hosts: set[str] = set()
    for network in networks:
        for host in iter_host_addresses(network):
            if host not in seen_hosts:
                seen_hosts.add(host)
                hosts.append(host)

    if not hosts:
        raise DiscoveryError("No host addresses available to scan.")

    token = probe_token or os.getenv("CDI_HEALTH_API_TOKEN") or None
    machines = registered_machines or []
    open_hosts: list[str] = []

    worker_count = min(64, max(4, len(hosts)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        port_futures = {
            executor.submit(is_port_open, host, port, timeout_seconds): host for host in hosts
        }
        for future in as_completed(port_futures):
            host = port_futures[future]
            try:
                if future.result():
                    open_hosts.append(host)
            except Exception:
                continue

    open_hosts.sort(key=ipaddress.IPv4Address)

    discovered: list[dict[str, Any]] = []
    if open_hosts:
        with ThreadPoolExecutor(max_workers=min(32, len(open_hosts))) as executor:
            probe_futures = {
                executor.submit(
                    _probe_discovered_host,
                    host,
                    port,
                    token,
                    timeout_seconds,
                    machines,
                ): host
                for host in open_hosts
            }
            for future in as_completed(probe_futures):
                try:
                    result = future.result()
                except Exception:
                    continue
                if result is not None:
                    discovered.append(result)

    discovered.sort(key=lambda item: ipaddress.IPv4Address(item["ip"]))
    duration_ms = int((time.monotonic() - started) * 1000)

    return {
        "scanned_subnets": subnet_values,
        "port": port,
        "hosts_scanned": len(hosts),
        "open_ports": len(open_hosts),
        "found": discovered,
        "duration_ms": duration_ms,
    }


def _probe_discovered_host(
    ip: str,
    port: int,
    probe_token: str | None,
    timeout_seconds: float,
    registered_machines: list[dict[str, Any]],
) -> dict[str, Any]:
    health = probe_cdi_health(
        ip,
        port,
        probe_token=probe_token,
        timeout_seconds=timeout_seconds,
    )
    hostname = reverse_hostname(ip)
    address = f"{ip}:{port}"
    cdi_api = health is not None and health.get("status") == "ok"

    return {
        "address": address,
        "ip": ip,
        "port": port,
        "hostname": hostname,
        "health": health,
        "cdi_api": cdi_api,
        "already_registered": is_already_registered(ip, port, registered_machines),
    }
