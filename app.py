"""Application factory and configuration for the Wellness Tracker."""

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask

from blueprints.api import api_bp
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.tracking import tracking_bp
from repository import InMemoryRepository, MongoRepository

PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: Any) -> bool:

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _make_repository(app: Flask):

    supplied_repository = app.config.get("REPOSITORY")

    if supplied_repository is not None:
        return supplied_repository

    if app.config.get("USE_MEMORY_DB"):
        return InMemoryRepository()

    try:
        repository = MongoRepository(
            uri=app.config["MONGO_URI"],
            database_name=app.config["MONGO_DB_NAME"],
            timeout_ms=app.config[
                "MONGO_SERVER_SELECTION_TIMEOUT_MS"
            ],
        )

        repository.ping()
        return repository

    except Exception as exc:
        # MongoDB is an external dependency during local setup.
        if not app.config.get("ALLOW_MEMORY_FALLBACK", True):
            raise

        app.logger.warning(
            "MongoDB is unavailable; using an in-memory "
            "repository for this run: %s",
            exc,
        )

        return InMemoryRepository()


def create_app(test_config: Dict[str, Any] = None) -> Flask:

    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY",
            "development-only-secret",
        ),
        MONGO_URI=os.environ.get(
            "MONGO_URI",
            "mongodb://localhost:27017",
        ),
        MONGO_DB_NAME=os.environ.get(
            "MONGO_DB_NAME",
            "wellness_tracker",
        ),
        MONGO_SERVER_SELECTION_TIMEOUT_MS=int(
            os.environ.get(
                "MONGO_SERVER_SELECTION_TIMEOUT_MS",
                "1000",
            )
        ),
        ALLOW_MEMORY_FALLBACK=_as_bool(
            os.environ.get(
                "ALLOW_MEMORY_FALLBACK",
                "true",
            )
        ),
        USE_MEMORY_DB=False,
    )

    # Test settings can override the .env configuration.
    if test_config:
        app.config.update(test_config)

    repository = _make_repository(app)

    app.extensions["repository"] = repository
    app.config["REPOSITORY_BACKEND"] = type(
        repository
    ).__name__

    # Register all Flask Blueprints.
    app.register_blueprint(main_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)