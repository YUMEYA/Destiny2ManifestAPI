from fastapi import Request

from .app import create_app

app = create_app()


@app.middleware("http")
async def lazy_engines(request: Request, call_next):
    from asyncio import Future

    from gino import create_engine

    from . import config
    from .app.models import dbname, engines

    name = request.query_params.get("lang", config.MANIFEST_LANG[0])
    dsn = config.PG_DB_MAPPING[name]
    fut = engines.get(name)
    if fut is None:
        fut = engines[name] = Future()
        try:
            engine = await create_engine(dsn)
        except Exception as e:
            fut.set_exception(e)
            del engines[name]
            raise
        else:
            fut.set_result(engine)
    await fut
    dbname.set(name)
    return await call_next(request)
