import os
import time
import socket
from datetime import datetime, timezone

import docker


# Docker client (reuse for all operations)
client = docker.from_env()


def get_free_port() -> int:
    """
    Ask the OS for a free TCP port on the host and return it.
    """
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_n8n_local(
    container_name: str,
    volume_name: str,
    encryption_key: str,
    expires_at: str,
) -> int:
    """
    Start a single n8n workspace container on this host.

    - container_name: e.g. "n8n_u-1843ab"
    - volume_name: e.g. "n8n_u-1843ab_data"
    - encryption_key: workspace-specific key
    - expires_at: ISO timestamp string; stored on labels for janitor
    Returns: host_port (int) that n8n is mapped to on the host.
    """
    base_domain = os.getenv("WORKSPACE_BASE_DOMAIN", "xcommand.cloud")
    host_port = get_free_port()

    # Derive subdomain from the container name "n8n_u-xxxxxx" -> "u-xxxxxx"
    subdomain = container_name.replace("n8n_", "")
    router_host = f"{subdomain}.{base_domain}"

    # n8n environment
    env = {
        # tell n8n the real public host + protocol (so links/cookies are correct)
        "N8N_HOST": router_host,
        "N8N_PORT": "5678",
        "N8N_PROTOCOL": "https",
        "N8N_ENCRYPTION_KEY": encryption_key,
        "N8N_DIAGNOSTICS_ENABLED": "false",
        "N8N_VERSION_NOTIFICATIONS_ENABLED": "false",
        "N8N_SECURE_COOKIE": "false",
        # Skip the user management wizard; we use basic auth instead
        "N8N_USER_MANAGEMENT_DISABLED": "true",
        "N8N_BASIC_AUTH_ACTIVE": "true",
        "N8N_BASIC_AUTH_USER": "admin",
        "N8N_BASIC_AUTH_PASSWORD": encryption_key[:16],
    }


    labels = {
        # internal janitor metadata
        "xcommand.workspace": "true",
        "xcommand.subdomain": subdomain,
        "xcommand.expires_at": expires_at,
    
        # Traefik routing
        "traefik.enable": "true",
        "traefik.docker.network": "n8n_web",
    
        # Router rules
        f"traefik.http.routers.{subdomain}.rule": f"Host(`{router_host}`)",
        f"traefik.http.routers.{subdomain}.entrypoints": "websecure",
    
        # 🔥 These were missing — REQUIRED for TLS
        f"traefik.http.routers.{subdomain}.tls": "true",
        f"traefik.http.routers.{subdomain}.tls.certresolver": "le",
    
        # Service points to the internal container port
        f"traefik.http.services.{subdomain}.loadbalancer.server.port": "5678",
    }


    # Create volume if it doesn't exist yet
    try:
        client.volumes.get(volume_name)
    except docker.errors.NotFound:
        client.volumes.create(name=volume_name)

    # Run the container
    container = client.containers.run(
        "n8nio/n8n:latest",
        detach=True,
        name=container_name,
        environment=env,
        volumes={
            volume_name: {
                "bind": "/home/node/.n8n",
                "mode": "rw",
            }
        },
        # Keep host port mapping so http://IP:PORT still works for debugging
        ports={"5678/tcp": host_port},
        # Put the container on the same network Traefik is using
        network="n8n_web",
        labels=labels,
    )

    # Give n8n some time to boot before we mark the workspace as "active"
    boot_wait_seconds = 25

    for _ in range(boot_wait_seconds):
        try:
            container.reload()
            if container.status != "running":
                time.sleep(1)
                continue
            break
        except docker.errors.APIError:
            time.sleep(1)

    time.sleep(5)
    return host_port


def stop_container(container_name: str) -> bool:
    """
    Stop a running workspace container by name.
    Returns True if it was found and stopped, False if it did not exist.
    """
    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        return False

    try:
        container.stop(timeout=30)
    except docker.errors.APIError:
        # Best effort; if stop fails we still return False
        return False

    return True


def remove_volume(volume_name: str) -> bool:
    """
    Remove a Docker volume by name.
    Returns True if removed, False if it didn't exist.
    """
    try:
        volume = client.volumes.get(volume_name)
    except docker.errors.NotFound:
        return False

    try:
        volume.remove(force=True)
    except docker.errors.APIError:
        return False

    return True
