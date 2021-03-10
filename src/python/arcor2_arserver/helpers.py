from contextlib import asynccontextmanager
from typing import Set, List, AsyncGenerator, Union

from arcor2.exceptions import Arcor2Exception, CannotLock
from arcor2_arserver.decorators import retry
from arcor2_arserver.globals import LOCK


def unique_name(name: str, existing_names: Set[str]) -> None:

    if not name:
        raise Arcor2Exception("Name has to be set.")

    if name in existing_names:
        raise Arcor2Exception("Name already exists.")


@retry(exc=CannotLock, tries=5, delay=0.5)
@asynccontextmanager
async def ctx_write_lock(obj_ids: Union[str, List[str]], owner: str = LOCK.SERVER_NAME) -> AsyncGenerator[None, None]:

    if isinstance(obj_ids, str):
        obj_ids = [obj_ids]

    locked = []
    for obj_id in obj_ids:
        if await LOCK.write_lock(obj_id, owner):
            locked.append(obj_id)
        else:
            for lock_obj in locked:
                # TODO handle unlock failure
                await LOCK.write_unlock(lock_obj, owner)
            raise CannotLock("Locking failed")
    try:
        yield
    finally:
        for obj_id in obj_ids:
            # TODO handle unlock failure
            await LOCK.write_unlock(obj_id, owner)


@retry(exc=CannotLock, tries=5, delay=0.5)
@asynccontextmanager
async def ctx_read_lock(obj_ids: Union[str, List[str]], owner: str) -> AsyncGenerator[None, None]:

    if isinstance(obj_ids, str):
        obj_ids = [obj_ids]

    locked = []
    for obj_id in obj_ids:
        if await LOCK.read_lock(obj_id, owner):
            locked.append(obj_id)
        else:
            for lock_obj in locked:
                # TODO handle unlock failure
                await LOCK.read_unlock(lock_obj, owner)
            raise CannotLock("Locking failed")
    try:
        yield
    finally:
        for obj_id in obj_ids:
            # TODO handle unlock failure
            await LOCK.read_unlock(obj_id, owner)


