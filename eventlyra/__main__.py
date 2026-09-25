"""Arranque: python -m eventlyra --sessions-per-gpu K"""

from __future__ import annotations

import logging

import uvicorn

from eventlyra.config import settings_from_argv
from eventlyra.server.app import create_app


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = settings_from_argv(argv)
    # reload=False a propósito: el reloader de uvicorn duplicaría el proceso y los pesos.
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
