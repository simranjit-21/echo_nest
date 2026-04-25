import os

from app import create_app

try:
    from waitress import serve
except ImportError:  # pragma: no cover - fallback for minimal environments
    serve = None


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    if serve is not None and os.getenv("USE_FLASK_DEV_SERVER", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=False)
