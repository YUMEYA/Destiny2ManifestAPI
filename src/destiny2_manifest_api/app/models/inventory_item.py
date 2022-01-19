from collections import defaultdict

from ...utils.constants import WATERMARK_SEASON_MAPPING, YEAR_SEASON_MAPPING
from ...utils.functions import aobject
from .base_model import BaseModel


class InventoryItem(BaseModel):
    __collection_name__ = "DestinyInventoryItemDefinition"

    @property
    def icon(self) -> str | None:
        if icon := self.displayProperties.get("icon"):
            return icon
        else:
            return None


from .plug_set import Plug, PlugSet
from .socket_category import SocketCategory
from .stat import Stat


class SocketInstance(aobject):
    async def __init__(self, **kwargs):
        if initial_item_hash := kwargs.get("singleInitialItemHash"):
            self.initial_item: Plug = await Plug(hash=initial_item_hash)
        else:
            self.initial_item = None

        if plug_set_hash := kwargs.get("randomizedPlugSetHash"):
            self.possible_items: list[Plug] = [
                plug async for plug in await PlugSet(hash=plug_set_hash)
            ]
        else:
            self.possible_items = None

        if plug_set_hash := kwargs.get("reusablePlugSetHash"):
            self.fixed_items: list[Plug] = [
                plug async for plug in await PlugSet(hash=plug_set_hash)
            ]
        else:
            self.fixed_items = None


class Socket(aobject):
    async def __init__(self, category_hash, socket_entry_list):
        self.category: SocketCategory = await SocketCategory(hash=category_hash)
        self.socket_instances: list[SocketInstance] = []
        for s in socket_entry_list:
            self.socket_instances.append(await SocketInstance(**s))


class Weapon(InventoryItem):
    async def __init__(
        self,
        hash: int | None = None,
        name: str | None = "",
        *,
        year: int | None = None,
        season: int | None = None,
    ):
        self.year = year
        self.season = season
        if self.year or self.season:
            additional_queries = self._gen_additional_queries()
        else:
            additional_queries = {}

        await super(Weapon, self).__init__(
            hash,
            name,
            additional_queries=additional_queries,
        )
        self._get_season_by_watermark()
        self._get_year_by_season()

    def _get_season_by_watermark(self):
        if watermark := self.iconWatermark:
            self.season = WATERMARK_SEASON_MAPPING.get(watermark)

    def _get_year_by_season(self):
        if year := [y for y, s in YEAR_SEASON_MAPPING.items() if self.season in s]:
            self.year = year[0]

    def _gen_additional_queries(self):
        additional_queries: dict = {"json.itemCategoryHashes": 1}
        if self.year == 1:
            if self.season == 1:
                additional_queries["json.iconWatermark"] = {"$exists": False}
            else:
                additional_queries[
                    "$or" : [
                        {"json.iconWatermark": {"$exists": False}},
                        {"json.iconWatermark": {"$in": self._get_watermarks()}},
                    ]
                ]
        else:
            additional_queries["json.iconWatermark"] = {"$in": self._get_watermarks()}
        return additional_queries

    def _get_watermarks(self) -> list[str]:
        watermarks: list[str] = []
        if self.season:
            watermarks = [
                wm for wm, ss in WATERMARK_SEASON_MAPPING.items() if ss == self.season
            ]
            return watermarks
        if self.year:
            seasons = YEAR_SEASON_MAPPING.get(self.year)
            watermarks = [
                wm for wm, ss in WATERMARK_SEASON_MAPPING.items() if ss in seasons
            ]
        return watermarks

    @property
    async def sockets(self) -> dict[str, list[SocketInstance]] | None:
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

    @property
    async def stats(self) -> dict[str, int | None] | None:
        if stats := self.raw.get("stats", {}).get("stats", {}):
            stats: dict[int, dict]
            stat_dict: dict[str, int | None] = {}
            for value in stats.values():
                stat: Stat = await Stat(value.get("statHash"))
                if stat.name:
                    stat_dict[stat.name] = value.get("value")
            return stat_dict
        else:
            return None

    async def as_dict(self) -> dict:
        sockets = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for key, socket_list in (await self.sockets).items():
            for index, socket in enumerate(socket_list):
                for attr in vars(socket).keys():
                    if (plugs := getattr(socket, attr, None)) is not None:
                        plugs: Plug | list[Plug]
                        if isinstance(plugs, Plug):
                            sockets[key][index][attr].append(plugs.name)
                        else:
                            [
                                sockets[key][index][attr].append(plug.name)
                                for plug in plugs
                            ]
        return {
            "hash": self.hash,
            "name": self.name,
            "year": self.year,
            "season": self.season,
            "stats": await self.stats,
            "sockets": sockets,
        }
