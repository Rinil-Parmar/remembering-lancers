import os

from waitress import serve

from remembering_lancers import create_app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    serve(app, host=host, port=port)
