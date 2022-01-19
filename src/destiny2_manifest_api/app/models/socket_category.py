from .base_model import BaseModel


class SocketCategory(BaseModel):
    __collection_name__ = "DestinySocketCategoryDefinition"
    name: str
