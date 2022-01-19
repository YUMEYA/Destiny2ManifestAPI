from ...utils.functions import aobject
from .base_model import BaseModel
from .stat import Stat


class PlugStat(aobject):
    stat: Stat
    value: str

    async def __init__(self, stat_hash: int, value: int):
        self.stat = await Stat(stat_hash)
        if value >= 0:
            self.value = f"+{value}"
        else:
            self.value = f"{value}"


from .inventory_item import InventoryItem


class Plug(InventoryItem):
    name: str
    investmentStats: list[dict]

    @property
    async def stats(self) -> list[PlugStat]:
        return [
            await PlugStat(invstat.get("statTypeHash"), invstat.get("value"))
            for invstat in self.investmentStats
            if self.investmentStats
        ]


class PlugSet(BaseModel):
    __collection_name__ = "DestinyPlugSetDefinition"

    async def __aiter__(self):
        for plug in self.reusablePlugItems:
            yield await Plug(hash=plug.get("plugItemHash"))
