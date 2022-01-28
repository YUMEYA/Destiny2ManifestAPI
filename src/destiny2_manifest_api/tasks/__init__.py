import asyncio

import tzlocal
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo.mongo_client import MongoClient

from ..config import MANIFEST_LANG, MONGO_URI
from ..utils.logging import create_logger

logger = create_logger("destiny_manifest_api.task", "task.log")


mongo = MongoClient(MONGO_URI)
jobstores = {"default": MongoDBJobStore(client=mongo)}
executors = {"default": AsyncIOExecutor()}
job_defaults = {"coalesce": False, "max_instances": 4}
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone=str(tzlocal.get_localzone_name()),
)


@scheduler.scheduled_job(
    trigger="cron",
    hour=1,
    id="update_manifest",
    name="update_manifest",
)
async def update_task():
    from .fetch_manifest import manifest_task

    tasks = [asyncio.create_task(manifest_task(lang)) for lang in MANIFEST_LANG]
    await asyncio.wait(tasks)
