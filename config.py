import os
from importlib.util import find_spec
from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(raw_url):
    if not raw_url:
        return "sqlite:///app.db"

    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # On Python 3.13+, psycopg (v3) is generally easier to install than psycopg2.
    # If the URL doesn't specify a driver and only psycopg is available, pick it.
    has_driver = "+psycopg" in url or "+psycopg2" in url
    if url.startswith("postgresql://") and not has_driver:
        if find_spec("psycopg") is not None and find_spec("psycopg2") is None:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
