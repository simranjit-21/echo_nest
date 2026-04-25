import os
import logging

from flask import Flask
from sqlmodel import SQLModel

from .auth import auth_bp, login_manager
from .database import ensure_schema, get_engine
from .env import load_dotenv
from .mood import mood_bp
from .utils import write_css

__all__ = ["create_app", "get_engine"]


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_app() -> Flask:
    load_dotenv()
    _configure_logging()
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///echo_nest.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    SQLModel.metadata.create_all(get_engine())
    ensure_schema()

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(mood_bp)

    write_css()
    app.logger.info("Echo_Nest app created.")

    return app
