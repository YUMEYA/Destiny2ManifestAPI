from asyncio import Future
from contextvars import ContextVar

from gino_starlette import Gino

from ... import config

engines = {}
dbname = ContextVar("dbname")


class ContextualGino(Gino):
    @property
    def bind(self):
        e: Future = engines.get(dbname.get(""))
        if e and e.done():
            return e.result()
        else:
            return self._bind

    @bind.setter
    def bind(self, val):
        self._bind = val


db = ContextualGino(dsn=config.PG_DEFAULT_DSN)
