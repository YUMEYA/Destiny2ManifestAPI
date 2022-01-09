from motor.motor_asyncio import AsyncIOMotorCollection

from ...utils.functions import aobject
from . import mongo


class BaseModel(aobject):
    __collection_name__ = ""

    async def __init__(self, hash: int = None, name: str = ""):
        if not self.__collection_name__:
            raise TypeError("Unknown collection name, ")
        self.collection: AsyncIOMotorCollection = mongo.db[self.__collection_name__]
        self.hash: int = hash
        self.name: str = name

        if self.hash:
            filter = {"_id": self.hash}
        elif self.name:
            filter = {"json.displayProperties.name": self.name}
        else:
            raise TypeError(
                f"Must provide either name or hash for {self.__class__.__name__}"
            )

        _raw: dict = await self.collection.find_one(filter)
        if not _raw:
            raise ValueError(
                f"Unknown {self.__class__.__name__}<name={self.name}, hash={self.hash}>"
            )

        self.hash: int = _raw.get("_id", None)
        self.name: str = (
            _raw.get("json", {}).get("displayProperties", {}).get("name", "")
        )
        self.raw: dict = _raw.get("json", {})

    def __getattr__(self, attr):
        if attr in self.raw.keys():
            return self.raw[attr]
        else:
            return None
