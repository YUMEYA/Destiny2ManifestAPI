from fastapi import APIRouter
from pydantic import BaseModel

from ..models.base_model import CannotFindEntity, MissingHashOrName
from ..models.inventory_item import Weapon

router = APIRouter(prefix="/weapon", tags=["Weapon"])


class WeaponModel(BaseModel):
    pass


@router.get("/", response_model=WeaponModel)
async def get_weapon(hash: int = 0, name: str = "", year: int = 0, season: int = 0):
    weapon = await Weapon(hash=hash, name=name, year=year, season=season)
