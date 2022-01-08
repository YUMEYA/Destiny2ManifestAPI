from fastapi import Request

from .app import create_app

app = create_app()


@app.middleware("http")
async def set_dbname(request: Request, call_next):
    from . import config
    from .app.models import dbname

    lang = request.query_params.get("lang", config.MANIFEST_LANG[0])
    dbname.set(f"{config.MANIFEST_DB_PREFIX}_{lang}")
    return await call_next(request)
