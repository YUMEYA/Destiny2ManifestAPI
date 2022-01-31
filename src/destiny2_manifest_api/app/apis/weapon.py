from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from ..models.inventory_item import Weapon

router = APIRouter(prefix="/weapon", tags=["Weapon"])


class WeaponModel(BaseModel):
    hash: int | None
    name: str | None
    year: int | None
    season: int | None
    stats: dict
    sockets: dict


@router.get("/", response_model=WeaponModel)
async def get_weapon(
    hash: int | None = None,
    name: str | None = None,
    year: int | None = None,
    season: int | None = None,
):
    weapon: Weapon = await Weapon(hash=hash, name=name, year=year, season=season)
    return await weapon.as_dict()


def init_app(app: FastAPI):
    app.include_router(router)
