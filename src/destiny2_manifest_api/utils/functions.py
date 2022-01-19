import asyncio
from functools import partial, wraps

from httpx import AsyncClient, Response

from .. import config


class ResponseError(Exception):
    def __init__(self, response: Response, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.response = response
        self.message = self.__str__()

    def __str__(self) -> str:
        return (
            f"{self.response.request.method} "
            f"{self.response.request.url}: "
            f"{self.response.status_code}\n"
            f"{self.response.request.headers}\n"
            f"{self.response.request.content}"
        )

    def __repr__(self) -> str:
        return self.__str__()


async def api_request(method: str, endpoint: str, **kwargs) -> Response:
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    url = f"{config.BUNGIE_API_ROOT}{endpoint}"
    kwargs = {**{"headers": {"X-API-Key": str(config.BUNGIE_API_KEY)}}, **kwargs}
    async with AsyncClient() as client:
        response: Response = await client.request(method, url, **kwargs)
    if not response.status_code == 200:
        raise ResponseError(response)
    return response


def async_wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run


class aobject(object):
    """
    Inheriting this class allows you to define an async __init__.

    So you can create objects by doing something like `await MyClass(params)`
    """

    async def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        await instance.__init__(*args, **kwargs)
        return instance

    async def __init__(self):
        pass
