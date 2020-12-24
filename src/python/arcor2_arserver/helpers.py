from contextlib import asynccontextmanager
from typing import Set, List, AsyncGenerator, Union

from arcor2.exceptions import Arcor2Exception
from arcor2_arserver.globals import LOCK


def unique_name(name: str, existing_names: Set[str]) -> None:

    if not name:
        raise Arcor2Exception("Name has to be set.")

    if name in existing_names:
        raise Arcor2Exception("Name already exists.")


@asynccontextmanager
async def ctx_write_lock(obj_ids: Union[str, List[str]], owner: str = LOCK.SERVER_NAME) -> AsyncGenerator[None, None]:

    if isinstance(obj_ids, int):
        obj_ids = [obj_ids]

    for obj_id in obj_ids:
        await LOCK.write_lock(obj_id, owner)
    try:
        yield
    finally:
        for obj_id in obj_ids:
            await LOCK.write_unlock(obj_id)


@asynccontextmanager
async def ctx_read_lock(obj_ids: Union[str, List[str]], owner: str) -> AsyncGenerator[None, None]:
    locked = []
    for obj_id in obj_ids:
        if await LOCK.read_lock(obj_id, owner):
            locked.append(obj_id)
        else:
            # for obj_id in locked: TODO
            #     await LOCK.read_unlock(obj_id)
            raise Arcor2Exception("Locking failed")
    try:
        yield
    finally:
        for obj_id in obj_ids:
            await LOCK.read_unlock(obj_id)
