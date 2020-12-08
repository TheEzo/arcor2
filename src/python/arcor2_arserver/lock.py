import asyncio
from datetime import datetime
from typing import Optional, Dict

from arcor2.cached import UpdateableCachedProject
from arcor2.cached import UpdateableCachedScene


class Lock:
    class Data:
        __slots__ = "owner", "timestamp"

        def __init__(self, owner, timestamp):
            self.owner = owner
            self.timestamp = timestamp

    class LockedObject:
        __slots__ = "read", "write"

        def __init__(self):

            # object id: { rpc: data }
            self.read: Dict[str, Dict[str, "Lock.Data"]] = {}
            # rpc: data
            self.write: Dict[str, "Lock.Data"] = {}

        def lock_for_read(self, obj_id: str, owner: str, rpc: str) -> bool:
            ...

        def lock_for_write(self, owner: str, rpc: str) -> bool:

            if self.read:
                # TODO maybe categorize RPC and allow lock?
                # TODO read should be short action, consider to use loop for write lock
                return False
            if rpc in self.write:
                return False

            self.write[rpc] = Lock.Data(owner, datetime.now())
            return True

        def write_unlock(self, rpc: str) -> bool:

            del self.write[rpc]
            return True

        def is_empty(self) -> bool:

            return not self.read and not self.write

    def __init__(
            self, scene: Optional["UpdateableCachedScene"] = None,
            project: Optional["UpdateableCachedProject"] = None
    ):
        assert scene or project

        self.scene = scene
        self.project = project

        self._lock = asyncio.Lock()
        self._locked_objects: Dict[str, "Lock.LockedObject"] = {}

    async def lock_for_read(self, obj_id: str, owner, rpc) -> bool:
        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            locked = lock_record.lock_for_read(obj_id, owner, rpc)

            if not locked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return locked

    async def lock_for_write(self, obj_id: str, owner, rpc: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            locked = lock_record.lock_for_write(owner, rpc)

            if not locked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return locked

    async def unlock_write(self, obj_id: str, rpc: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            unlocked = lock_record.write_unlock(rpc)

            if unlocked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return unlocked

    def get_root_id(self, obj_id):
        """Retrieve root object id for given object"""

        if self.scene:
            # TODO scene object hierarchy
            return obj_id

        else:
            obj = self.project.action_point(obj_id)
            return obj.parent if obj.parent else obj_id

    def _get_lock_record(self, root_id: str) -> "Lock.LockedObject":
        """Create or retrieve lock record for root_id"""

        assert self._lock.locked()

        if root_id not in self._locked_objects:
            self._locked_objects[root_id] = Lock.LockedObject()

        return self._locked_objects[root_id]
