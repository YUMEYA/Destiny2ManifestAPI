from .base_model import BaseModel


class PlugSet(BaseModel):
    __collection_name__ = "DestinyPlugSetDefinition"

    async def __aiter__(self):
        from .inventory_item import InventoryItem

        for plug in self.reusablePlugItems:
            yield await InventoryItem(hash=plug.get("plugItemHash"))
