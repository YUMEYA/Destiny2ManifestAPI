import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
import aiosqlite
from httpx import AsyncClient, Response
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .. import config
from ..utils.functions import aobject, api_request, async_wrap
from . import logger


class Manifest(aobject):
    async def __init__(self, language) -> None:
        self.language = language
        self.version = ""
        self.manifest_origin_path = ""
        self.manifest_download_dir = config.MANIFEST_SAVE_DIR / "zip"
        self.manifest_download_dir.mkdir(0o755, parents=True, exist_ok=True)
        self.manifest_download_filename = f"{self.language}.zip"
        self.manifest_sqlite_dir = config.MANIFEST_SAVE_DIR / "sqlite"
        self.manifest_sqlite_dir.mkdir(0o755, parents=True, exist_ok=True)
        self.manifest_sqlite_filename = f"{self.language}.content"
        self.manifest_mongo_dbname = f"{config.MANIFEST_DB_PREFIX}_{self.language}"
        self.manifest_mongo_uri = config.MONGO_URI

        await self.__check_origin_manifest()
        self.mongo: AsyncIOMotorDatabase = AsyncIOMotorClient(self.manifest_mongo_uri)[
            self.manifest_mongo_dbname
        ]

    async def __check_origin_manifest(self) -> None:
        resp: Response = await api_request("GET", "/Destiny2/Manifest/")
        resp_json: dict = resp.json()
        if resp_json.get("ErrorCode") == 1 or resp_json.get("ErrorStatus") == "Success":
            resp_json: dict = resp_json.get("Response", {})

        if (version := resp_json.get("version", "")) and (
            manifest_origin_path := resp_json.get("mobileWorldContentPaths", {}).get(
                self.language, ""
            )
        ):
            await logger.info(f"Origin manifest version: {version}")
            await logger.info(f"Origin path: {manifest_origin_path}")
            self.version: str = version
            self.manifest_origin_path: str = manifest_origin_path

    @property
    async def is_outdated(self):
        doc = await self.mongo["manifest_version"].find_one({"_id": 1})
        if not doc:
            await logger.info("Cannot get local manifest version")
            version = None
        else:
            version: str = doc.get("version", "")
        if version != self.version:
            return True
        return False

    async def download_manifest(self) -> None:
        download_url: str = f"{config.BUNGIE_API_HOST}{self.manifest_origin_path}"
        download_path: Path = (
            self.manifest_download_dir / self.manifest_download_filename
        )
        await logger.info(
            f"Downloading manifest from {download_url} to {download_path}"
        )
        async with AsyncClient() as client:
            async with client.stream("GET", download_url) as response:
                async with aiofiles.open(download_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)
        await logger.info("Download Complete")

    @async_wrap
    def unzip_manifest(self) -> None:
        zip_filepath: Path = (
            self.manifest_download_dir / self.manifest_download_filename
        )
        if zipfile.is_zipfile(zip_filepath):
            with zipfile.ZipFile(zip_filepath, "r") as zf:
                unzip_file = zf.infolist()[0]
                unzip_file.filename = self.manifest_sqlite_filename
                zf.extract(unzip_file, self.manifest_sqlite_dir)

    async def iter_sqlite_tables(self):
        async with aiosqlite.connect(
            self.manifest_sqlite_dir / self.manifest_sqlite_filename
        ) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE `type`='table' order by name;"
            ) as cursor:
                async for row in cursor:
                    tablename: str = row["name"]
                    table_meta = {}
                    async with await db.execute(
                        f"pragma table_info({tablename})"
                    ) as table_metas:
                        async for meta_row in table_metas:
                            table_meta[meta_row["name"]] = {
                                "name": meta_row["name"],
                                "type": meta_row["type"],
                                "pk": meta_row["pk"],
                            }
                    yield tablename, table_meta

    async def iter_sqlite_table_data(self, tablename: str):
        await logger.info(f"Fetching data from table [{tablename}]")
        async with aiosqlite.connect(
            self.manifest_sqlite_dir / self.manifest_sqlite_filename
        ) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f"SELECT * FROM {tablename};") as cursor:
                async for row in cursor:
                    yield row

    def int_signed_to_unsigned(self, integer: int) -> int:
        try:
            int(integer)
        except ValueError:
            return integer
        if not isinstance(integer, int) or integer >= 0:
            return integer
        return integer + (1 << 32)

    async def iter_insert_batch(
        self,
        data_src: AsyncGenerator[aiosqlite.Row, None],
        table_meta: dict[dict[str]],
        batch_size=1000,
    ):
        counter = 0
        batch = []
        async for data_row in data_src:
            for data_key in data_row.keys():
                _meta = table_meta[data_key]
                if _meta["pk"] == 1:
                    _id = self.int_signed_to_unsigned(data_row[data_key])
                elif _meta["name"] == "json":
                    _json = json.loads(data_row[data_key])

            row_value = {"_id": _id, "json": _json}

            counter += 1
            batch.append(row_value)
            if counter >= batch_size:
                yield batch
                counter = 0
                batch = []
        if batch:
            yield batch

    async def batch_insert(self, tablename, batch: list) -> None:
        try:
            await logger.info(f"Inserting into collection [{tablename}]")
            await self.mongo[tablename].insert_many(batch)
        except Exception as e:
            await logger.exception(e)

    async def update_version(self) -> None:
        await self.mongo["manifest_version"].update_one(
            {"_id": 1},
            {
                "$set": {
                    "version": self.version,
                    "update_time": datetime.now(),
                }
            },
            upsert=True,
        )

    async def migrate_data(
        self,
        tablename: str,
        table_meta: dict[dict[str]],
    ) -> None:
        try:
            await self.mongo[tablename].drop()
        except Exception as e:
            await logger.exception(e)

        async for batch in self.iter_insert_batch(
            self.iter_sqlite_table_data(tablename), table_meta
        ):
            await self.batch_insert(tablename, batch)
        await self.update_version()


async def manifest_task(language):
    manifest: Manifest = await Manifest(language)
    if await manifest.is_outdated:
        await logger.info("Local manifest is outdated, updating")
        await manifest.download_manifest()
        await manifest.unzip_manifest()
        async for table, meta in manifest.iter_sqlite_tables():
            await manifest.migrate_data(table, meta)
        await logger.info("Local manifest update complete")
    else:
        await logger.info("Local manifest is up to date")
