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


DEBUG = config("DEBUG", cast=bool, default=False)
SECRET_KEY = config("SECRET_KEY", cast=Secret, default=token_urlsafe(64))
LOG_LEVEL = config("LOG_LEVEL", cast=logging.getLevelName, default="INFO")
LOG_FILE_PATH: Path = config("LOG_FILE_PATH", cast=Path, default=BASE_DIR / "log")
MANIFEST_SAVE_DIR: Path = config(
    "MANIFEST_SAVE_DIR", cast=Path, default=BASE_DIR / "manifest"
)
MANIFEST_LANG = config("MANIFEST_LANG", cast=CommaSeparatedStrings, default="zh-cht")
MANIFEST_DB_PREFIX = config("MANIFEST_DB_PREFIX", default="destiny2_manifest")
BUNGIE_API_HOST = config("BUNGIE_API_HOST", default="https://www.bungie.net")
BUNGIE_API_ROOT = config("BUNGIE_API_ROOT", default=f"{BUNGIE_API_HOST}/Platform")
BUNGIE_API_KEY = config("BUNGIE_API_KEY", cast=Secret)
PG_HOST = config("PG_HOST", default="localhost")
PG_PORT = config("PG_PORT", cast=int, default="5432")
PG_USERNAME = config("PG_USERNAME", default=None)
PG_PASSWORD = config("PG_PASSWORD", cast=Secret, default=None)

PG_DB_MAPPING = {
    lang: f"postgresql://{PG_USERNAME}:{str(PG_PASSWORD)}@"
    f"{PG_HOST}:{PG_PORT}/{MANIFEST_DB_PREFIX}_{lang}"
    for lang in MANIFEST_LANG
}
PG_DEFAULT_DSN = PG_DB_MAPPING[MANIFEST_LANG[0]]
LOG_FILE_PATH.mkdir(parents=True, exist_ok=True)
MANIFEST_SAVE_DIR.mkdir(parents=True, exist_ok=True)
