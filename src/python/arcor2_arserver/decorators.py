import functools
from asyncio import sleep
from typing import Any, Callable, Coroutine, TypeVar, cast

from arcor2.exceptions import Arcor2Exception
from arcor2_arserver import globals as glob

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def no_scene(coro: F) -> F:
    @functools.wraps(coro)
    async def async_wrapper(*args, **kwargs) -> Any:

        if glob.SCENE:
            raise Arcor2Exception("Scene has to be closed first.")
        return await coro(*args, **kwargs)

    return cast(F, async_wrapper)


def scene_needed(coro: F) -> F:
    @functools.wraps(coro)
    async def async_wrapper(*args, **kwargs) -> Any:

        if glob.SCENE is None or not glob.SCENE.id:
            raise Arcor2Exception("Scene not opened or has invalid id.")
        return await coro(*args, **kwargs)

    return cast(F, async_wrapper)


def no_project(coro: F) -> F:
    @functools.wraps(coro)
    async def async_wrapper(*args, **kwargs) -> Any:
        if glob.PROJECT:
            raise Arcor2Exception("Not available during project editing.")
        return await coro(*args, **kwargs)

    return cast(F, async_wrapper)


def project_needed(coro: F) -> F:
    @functools.wraps(coro)
    async def async_wrapper(*args, **kwargs) -> Any:

        if glob.PROJECT is None or not glob.PROJECT.id:
            raise Arcor2Exception("Project not opened or has invalid id.")
        return await coro(*args, **kwargs)

    return cast(F, async_wrapper)


def retry(exc=Exception, tries: int = 1, delay: float = 0):
    """
    Retry decorator
    :param exc: Exception or tuple of exceptions to catch
    :param tries: number of attempts
    :param delay: delay between attempts
    """

    def _retry(coro: F) -> F:
        @functools.wraps(coro)
        async def async_wrapper(*fargs, **fkwargs) -> Any:
            return await _retry_call(exc, tries, delay, coro, *fargs, **fkwargs)

        return cast(coro, async_wrapper)

    return _retry


async def _retry_call(exc: Exception, tries: int, delay: float, coro: F, *args, **kwargs):
    """
    Internal part of retry decorator
    - handles exceptions, delay and tries
    """
    while tries:
        try:
            return await coro(*args, **kwargs)
        except exc:
            tries -= 1
            if tries == 0:
                raise

            if delay > 0:
                await sleep(delay)
