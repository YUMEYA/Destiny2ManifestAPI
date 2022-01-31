from importlib.metadata import entry_points

from fastapi import FastAPI, Request

from ..utils.logging import create_logger

logger = create_logger("destiny_manifest_api.app", "app.log")


def load_modules(app=None):
    for ep in entry_points()["destiny2_manifest_api.modules"]:
        mod = ep.load()
        if app:
            init_app = getattr(mod, "init_app", None)
            if init_app:
                init_app(app)


def create_app():
    from .. import config
    from .models import dbname, mongo

    app = FastAPI(title="Destiny 2 Manifest API", debug=config.DEBUG)
    mongo.init_app(app)
    load_modules(app)

    @app.middleware("http")
    async def set_dbname(request: Request, call_next):
        lang = request.query_params.get("lang", config.MANIFEST_LANG[0])
        dbname.set(f"{config.MANIFEST_DB_PREFIX}_{lang}")
        return await call_next(request)

    from fastapi.responses import JSONResponse

    from .models.base_model import CannotFindEntity, MissingHashOrName

    @app.exception_handler(CannotFindEntity)
    async def cannot_find_entity_handler(request: Request, exc: CannotFindEntity):
        return JSONResponse({"message": exc.message}, 404)

    @app.exception_handler(MissingHashOrName)
    async def missing_hash_or_name_handler(request: Request, exc: MissingHashOrName):
        return JSONResponse({"message": exc.message}, 400)

    @app.on_event("startup")
    async def run_schduler():
        from datetime import datetime

        from ..tasks import scheduler, update_task

        scheduler.add_job(
            update_task,
            trigger="cron",
            hour=1,
            id="update_manifest",
            name="update_manifest",
            replace_existing=True,
        )
        scheduler.start()
        scheduler.modify_job("update_manifest", next_run_time=datetime.now())

    return app
