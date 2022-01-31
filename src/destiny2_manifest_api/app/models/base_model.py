from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING
from ...utils.functions import aobject
from . import mongo


class UnknownCollectionName(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class MissingHashOrName(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class CannotFindEntity(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class BaseModel(aobject):
    __collection_name__: str = ""

    collection: AsyncIOMotorCollection
    hash: int | None
    name: str
    raw: dict

    async def __init__(
        self,
        hash: int | None = None,
        name: str = "",
        *,
        additional_queries: dict = {},
    ):
        if not self.__collection_name__:
            raise UnknownCollectionName("Unknown collection name.")

        self.collection: AsyncIOMotorCollection = mongo.db[self.__collection_name__]
        self.hash: int | None = hash
        self.name: str = name
        self.raw: dict = {}

        if self.hash:
            filter = {"_id": self.hash}
        elif self.name:
            filter = {"json.displayProperties.name": self.name}
        else:
            raise MissingHashOrName(
                f"Must provide either name or hash for {self.__class__.__name__}"
            )
        if additional_queries:
            filter = {**filter, **additional_queries}
        _raw: dict = await self.collection.find_one(
            filter, sort=[("json.index", DESCENDING)]
        )
        if not _raw:
            raise CannotFindEntity(
                f"Unknown {self.__class__.__name__} <name={self.name}, hash={self.hash}>"
            )

        self.hash = _raw.get("_id", None)
        self.name = _raw.get("json", {}).get("displayProperties", {}).get("name", "")
        self.raw = _raw.get("json", {})

    def __getattr__(self, attr):
        if attr in self.raw.keys():
            return self.raw[attr]
        else:
            return None
