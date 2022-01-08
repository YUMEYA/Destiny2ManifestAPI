from contextvars import ContextVar

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from ... import config
from ...utils.functions import aobject

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


class BaseModel(aobject):
    __collection_name__ = ""

    async def __init__(self, hash: int = None, name: str = ""):
        if not self.__collection_name__:
            raise TypeError("Unknown collection name, ")
        self.collection = mongo.db[self.__collection_name__]
        self.hash = hash
        self.name = name

        if self.hash:
            _raw = await self.collection.find_one({"_id": hash})
            self.name = (
                _raw.get("json", {}).get("displayProperties", {}).get("name", "")
            )
        elif self.name:
            _raw = await self.collection.find_one({"json.displayProperties.name": name})
            self.hash = _raw.get("_id", None)
        else:
            raise TypeError("Must provide either name or hash")
        if not _raw:
            raise ValueError(
                f"Unknown {self.__class__.__name__}<name={self.name}, hash={self.hash}>"
            )
        self.raw = _raw.get("json", {})
