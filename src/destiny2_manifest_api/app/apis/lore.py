from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from ..models import mongo
from ..models.lore import Lore

router = APIRouter(prefix="/lore", tags=["Lore"])


class LoreModel(BaseModel):
    title: str
    subtitle: str
    content: str


@router.get("/", response_model=LoreModel)
async def get_lore(
    hash: int | None = None,
    name: str | None = None,
):
    if not hash and not name:
        async for doc in mongo.db[Lore.__collection_name__].aggregate(
            [
                {"$match": {"json.displayProperties.description": {"$ne": ""}}},
                {
                    "$sample": {
                        "size": 1,
                    }
                },
            ]
        ):
            hash = doc.get("_id")
            break
        lore: Lore = await Lore(hash)
    else:
        lore: Lore = await Lore(hash, name)

    return lore.as_dict()


def init_app(app: FastAPI):
    app.include_router(router)
