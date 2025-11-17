import os
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

    # n8n environment
    env = {
        "N8N_HOST": "localhost",
        "N8N_PORT": "5678",
        "N8N_PROTOCOL": "http",
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

    # Labels for janitor + Traefik
    labels = {
        # internal janitor metadata
        "xcommand.workspace": "true",
        "xcommand.subdomain": subdomain,
        "xcommand.expires_at": expires_at,
        # Traefik routing: https://<subdomain>.<base_domain> -> this container:5678
        "traefik.enable": "true",
        f"traefik.http.routers.{subdomain}.rule": f"Host(`{subdomain}.{base_domain}`)",
        f"traefik.http.services.{subdomain}.loadbalancer.server.port": "5678",
        "traefik.docker.network": "n8n_web",
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
        # Keep host port mapping so http://IP:PORT still works
        ports={"5678/tcp": host_port},
        # Put the container on the same network Traefik is using
        network="n8n_web",
        labels=labels,
    )

    # Optionally we could wait for container to be healthy, but for now just return
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
