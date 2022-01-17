import logging
import os
from pathlib import Path
from secrets import token_urlsafe

from dotenv import load_dotenv
from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, Secret

BASE_DIR = Path(os.path.dirname(__file__)).absolute()

load_dotenv(BASE_DIR / ".env")
environment = os.getenv("ENVIRONMENT", None) or "dev"
config = Config(BASE_DIR / f".env.{environment}")


DEBUG: bool = config("DEBUG", cast=bool, default=False)
SECRET_KEY: Secret = config("SECRET_KEY", cast=Secret, default=token_urlsafe(64))
LOG_LEVEL = config("LOG_LEVEL", cast=logging.getLevelName, default="INFO")
LOG_FILE_PATH: Path = config("LOG_FILE_PATH", cast=Path, default=BASE_DIR / "log")

MANIFEST_SAVE_DIR: Path = config(
    "MANIFEST_SAVE_DIR", cast=Path, default=BASE_DIR / "manifest"
)
MANIFEST_LANG: list = config(
    "MANIFEST_LANG", cast=CommaSeparatedStrings, default="zh-cht"
)
MANIFEST_DB_PREFIX: str = config("MANIFEST_DB_PREFIX", default="destiny2_manifest")

BUNGIE_API_HOST: str = config("BUNGIE_API_HOST", default="https://www.bungie.net")
BUNGIE_API_ROOT: str = config("BUNGIE_API_ROOT", default=f"{BUNGIE_API_HOST}/Platform")
BUNGIE_API_KEY: Secret = config("BUNGIE_API_KEY", cast=Secret)

MONGO_HOST: str = config("MONGO_HOST", default="localhost")
MONGO_PORT: int = config("MONGO_PORT", cast=int, default="27017")
MONGO_USERNAME: str = config("MONGO_USERNAME", default="")
MONGO_PASSWORD: Secret = config("MONGO_PASSWORD", cast=Secret, default="")
MONGO_URI: str = (
    f"mongodb://{MONGO_USERNAME}:{str(MONGO_PASSWORD)}@"
    f"{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
)

LOG_FILE_PATH.mkdir(parents=True, exist_ok=True)
MANIFEST_SAVE_DIR.mkdir(parents=True, exist_ok=True)
