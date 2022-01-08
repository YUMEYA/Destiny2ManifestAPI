import zipfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
import aiosqlite
import asyncpg
from httpx import AsyncClient, Response

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
        self.manifest_pg_dbname = f"{config.MANIFEST_DB_PREFIX}_{self.language}"
        self.manifest_pg_dsn = config.PG_DB_MAPPING.get(self.language)

        self.pg_conn_pool = await self.__get_pg_conn_pool()
        await self.__check_origin_manifest()

    async def __get_pg_conn_pool(self) -> asyncpg.Pool:

        try:
            await logger.debug(f"Connecting to database: {self.manifest_pg_dsn}")
            conn_pool: asyncpg.Pool = await asyncpg.create_pool(self.manifest_pg_dsn)
        except asyncpg.exceptions.InvalidCatalogNameError:
            await logger.info(
                f"Database {self.manifest_pg_dbname} not exists, creating new database..."
            )
            sys_conn: asyncpg.Connection = await asyncpg.connect(
                host=config.PG_HOST,
                port=config.PG_PORT,
                user=config.PG_USERNAME,
                password=str(config.PG_PASSWORD),
                database="postgres",
            )
            await sys_conn.execute(
                f'CREATE DATABASE "{self.manifest_pg_dbname}" OWNER "{config.PG_USERNAME}"'
            )
            await sys_conn.close()
            conn_pool: asyncpg.Pool = await asyncpg.create_pool(self.manifest_pg_dsn)
        return conn_pool

    @property
    async def is_outdated(self):
        async with self.pg_conn_pool.acquire() as pg:
            pg: asyncpg.Connection
            try:
                verison = await pg.fetchval(
                    "SELECT version FROM public.manifest_version;"
                )
                await logger.info(f"Local manifest version: {verison}")
            except asyncpg.exceptions.UndefinedTableError:
                await logger.info("Cannot get local manifest version")
                await pg.execute(
                    "CREATE TABLE IF NOT EXISTS public.manifest_version ("
                    "id INTEGER PRIMARY KEY NOT NULL,"
                    "version TEXT NOT NULL,"
                    "update_time TIMESTAMP NOT NULL"
                    ");"
                )
                verison = await pg.fetchval(
                    "SELECT version FROM public.manifest_version;"
                )
        if verison != self.version:
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
                    table_meta = []
                    async with await db.execute(
                        f"pragma table_info({tablename})"
                    ) as table_metas:
                        async for meta_row in table_metas:
                            table_meta.append(
                                {
                                    "name": meta_row["name"],
                                    "type": "BIGINT"
                                    if meta_row["type"] == "INTEGER"
                                    else meta_row["type"],
                                    "pk": meta_row["pk"],
                                }
                            )
                    yield tablename, table_meta

    async def create_pg_table(self, tablename: str, meta: list) -> None:
        await logger.info(f"Create table [{tablename}] if not exists")
        async with self.pg_conn_pool.acquire() as pg:
            pg: asyncpg.Connection
            await pg.execute(
                f"CREATE TABLE IF NOT EXISTS public.{tablename} ("
                f"{meta[0].get('name','id')} {meta[0].get('type','BIGINT')} PRIMARY KEY NOT NULL,"
                f"{meta[1].get('name','json')} JSONB NULL"
                ");"
            )

    async def truncate_pg_table(self, tablename: str) -> None:
        await logger.info(f"Truncating table [{tablename}]")
        async with self.pg_conn_pool.acquire() as pg:
            pg: asyncpg.Connection
            await pg.execute(f"TRUNCATE TABLE public.{tablename};")

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
        if integer < 0:
            return integer + (1 << 32)
        return integer

    async def iter_insert_batch(
        self,
        data_src: AsyncGenerator[aiosqlite.Row, None],
        table_meta: list,
        batch_size=1000,
    ):
        counter = 0
        stmts = []
        async for data_row in data_src:
            row_value = []
            for data_key in data_row.keys():
                if (data_key == table_meta[0].get("name", "")) and (
                    "INT" in table_meta[0].get("type", "")
                ):
                    row_value.append(self.int_signed_to_unsigned(data_row[data_key]))
                else:
                    row_value.append(f"{data_row[data_key]}")
            counter += 1
            stmts.append(tuple(row_value))
            if counter >= batch_size:
                yield stmts
                counter = 0
                stmts = []
        if stmts:
            yield stmts

    async def insert_pg_table_data(
        self, tablename: str, table_meta: list, values: list = []
    ) -> None:
        await logger.info(f"Inserting into table [{tablename}]")
        sql = (
            f"INSERT INTO public.{tablename} "
            f"({table_meta[0].get('name','id')}, {table_meta[1].get('name','json')}) "
            f"VALUES ($1, $2);"
        )
        async with self.pg_conn_pool.acquire() as pg:
            pg: asyncpg.Connection
            async with pg.transaction():
                try:
                    await pg.executemany(sql, values)
                except Exception as e:
                    await logger.debug(sql)
                    await logger.exception("Insert Error!")
                    raise e

    async def update_version(self):
        await self.truncate_pg_table("manifest_version")
        async with self.pg_conn_pool.acquire() as pg:
            pg: asyncpg.Connection
            await pg.execute(
                "INSERT INTO public.manifest_version(id, version, update_time) "
                "values ($1, $2, $3)"
                "ON CONFLICT (id) "
                "DO UPDATE SET version=$2, update_time=$3;",
                *(1, self.version, datetime.now()),
            )

    async def migrate_data(
        self,
        tablename: str,
        table_meta: list,
    ):
        await self.create_pg_table(tablename, table_meta)
        await self.truncate_pg_table(tablename)
        async for stmt in self.iter_insert_batch(
            self.iter_sqlite_table_data(tablename), table_meta
        ):
            await self.insert_pg_table_data(tablename, table_meta, stmt)
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
