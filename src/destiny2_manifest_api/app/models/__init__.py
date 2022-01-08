from contextvars import ContextVar

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from ... import config

dbname = ContextVar(
    "dbname", default=f"{config.MANIFEST_DB_PREFIX}_{config.MANIFEST_LANG[0]}"
)


class ContextualMongo:
    def __init__(
        self,
        app: FastAPI = None,
        uri: str = "",
        *,
        host: str = "localhost",
        port: int = 27017,
        user: str = "",
        password: str = "",
        db: str = "local",
        authSource: str = "admin",
        replicaSet: str = "",
    ) -> None:
        self.uri = (
            uri
            if uri
            else (
                f"mongodb://{user}:{password}@"
                f"{host}:{port}/{db}?"
                f"authSource={authSource}"
                f"{f'&replicaSet={replicaSet}' if replicaSet else ''}"
            )
        )
        self.client = AsyncIOMotorClient(self.uri)
        if app:
            self.init_app(app)

    def init_app(self, app: FastAPI):
        self.app = app

    @property
    def db(self):
        self._db = self.client[dbname.get()]
        return self._db


mongo = ContextualMongo(uri=config.MONGO_URI)
