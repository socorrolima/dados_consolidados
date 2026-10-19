import os


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-only-not-secret"


class ProdConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    REQUIRED_ENV_VARS = ("DATABASE_URL", "SECRET_KEY")


CONFIG_BY_NAME = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,
}
