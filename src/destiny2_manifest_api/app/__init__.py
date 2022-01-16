from fastapi import FastAPI, Request

from .. import config
from ..utils.logging import create_logger
from .models import dbname, mongo

logger = create_logger("destiny_manifest_api.app", "app.log")


def create_app():
    app = FastAPI(title="Destiny 2 Manifest API", debug=config.DEBUG)
    mongo.init_app(app)

    @app.middleware("http")
    async def set_dbname(request: Request, call_next):
        lang = request.query_params.get("lang", config.MANIFEST_LANG[0])
        dbname.set(f"{config.MANIFEST_DB_PREFIX}_{lang}")
        return await call_next(request)

    return app
