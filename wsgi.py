import os

from app import create_app  # já carrega o .env (ver app/__init__.py)

app = create_app()

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
