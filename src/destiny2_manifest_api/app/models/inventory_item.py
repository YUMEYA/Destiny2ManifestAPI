from ...utils.constants import WATERMARK_SEASON_MAPPING
from ...utils.functions import aobject
from .base_model import BaseModel
from .plug_set import PlugSet
from .socket_category import SocketCategory


class SocketInstance(aobject):
    async def __init__(self, **kwargs):
        if initial_item_hash := kwargs.get("singleInitialItemHash"):
            self.initial_item: InventoryItem = await InventoryItem(
                hash=initial_item_hash
            )
        else:
            self.initial_item = None

        if plug_set_hash := kwargs.get("randomizedPlugSetHash"):
            self.possible_items: PlugSet = await PlugSet(hash=plug_set_hash)
        else:
            self.possible_items = None

        if plug_set_hash := kwargs.get("reusablePlugSetHash"):
            self.fixed_items: PlugSet = await PlugSet(hash=plug_set_hash)
        else:
            self.fixed_items = None


class Socket(aobject):
    async def __init__(self, category_hash, socket_entry_list):
        self.category: SocketCategory = await SocketCategory(hash=category_hash)
        self.socket_instances: list[SocketInstance] = []
        for s in socket_entry_list:
            self.socket_instances.append(await SocketInstance(**s))


class InventoryItem(BaseModel):
    __collection_name__ = "DestinyInventoryItemDefinition"

    @property
    def season(self) -> str:
        if wm := self.iconWatermark:
            return WATERMARK_SEASON_MAPPING.get(wm)

    @property
    async def sockets(self) -> dict[str, list[SocketInstance]]:
        if sockets := self.raw.get("sockets"):
            sockets: dict
            socket_dict: dict[str, list[SocketInstance]] = {}
            for category in sockets.get("socketCategories"):
                category: dict
                socket_entry_list = [
                    s
                    for idx, s in enumerate(sockets.get("socketEntries", []))
                    if idx in category.get("socketIndexes", [])
                ]
                _socket: Socket = await Socket(
                    category.get("socketCategoryHash", ""), socket_entry_list
                )
                socket_dict[_socket.category.name] = _socket.socket_instances

            return socket_dict
        else:
            return None
