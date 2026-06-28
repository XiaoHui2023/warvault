from __future__ import annotations

import socket
import logging

import uvicorn

from app_main.app import create_app
from app_main.config import load_config, set_config_path
from app_main.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def _lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def run_server(port: int | None = None, config_path: str | None = None) -> None:
    set_config_path(config_path)
    app_config = load_config(config_path)
    log_session_dir = setup_logging(app_config.logging)
    host = app_config.server.host
    base_url = app_config.server.base_url
    requested_port = app_config.server.port if port is None else port
    config = uvicorn.Config(
        create_app(config_path=config_path),
        host=host,
        port=requested_port,
        log_level="info",
        log_config=None,
    )
    server = uvicorn.Server(config)
    original_startup = server.startup

    async def startup_with_urls(sockets=None):
        await original_startup(sockets=sockets)
        actual_port = requested_port
        if server.servers:
            sockets_for_server = server.servers[0].sockets
            if sockets_for_server:
                actual_port = sockets_for_server[0].getsockname()[1]
        lan_url = f"http://{_lan_ip()}:{actual_port}{base_url}"
        local_url = f"http://127.0.0.1:{actual_port}{base_url}"
        logger.info("Service listening on %s:%s", host, actual_port)
        logger.info("Local: %s", local_url)
        logger.info("LAN: %s", lan_url)
        if log_session_dir is not None:
            logger.info("Logs: %s", log_session_dir)
        print(f"Service listening on {host}:{actual_port}", flush=True)
        print(f"Local: {local_url}", flush=True)
        print(f"LAN: {lan_url}", flush=True)
        if log_session_dir is not None:
            print(f"Logs: {log_session_dir}", flush=True)

    server.startup = startup_with_urls
    server.run()
