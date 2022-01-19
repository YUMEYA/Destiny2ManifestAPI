from fastapi import FastAPI, Request

from ..utils.logging import create_logger

logger = create_logger("destiny_manifest_api.app", "app.log")


def create_app():
    from .. import config
    from .models import dbname, mongo

    app = FastAPI(title="Destiny 2 Manifest API", debug=config.DEBUG)
    mongo.init_app(app)

    @app.middleware("http")
    async def set_dbname(request: Request, call_next):
        lang = request.query_params.get("lang", config.MANIFEST_LANG[0])
        dbname.set(f"{config.MANIFEST_DB_PREFIX}_{lang}")
        return await call_next(request)

    from .models.base_model import CannotFindEntity, MissingHashOrName
    from fastapi.responses import JSONResponse

    @app.exception_handler(CannotFindEntity)
    async def cannot_find_entity_handler(request: Request, exc: CannotFindEntity):
        return JSONResponse({"message": exc.message}, 404)

    @app.exception_handler(MissingHashOrName)
    async def missing_hash_or_name_handler(request: Request, exc: MissingHashOrName):
        return JSONResponse({"message": exc.message}, 400)

    return app
