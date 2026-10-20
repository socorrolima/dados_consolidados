import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402 — precisa rodar depois do load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
