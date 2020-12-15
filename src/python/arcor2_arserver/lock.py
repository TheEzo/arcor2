import asyncio
from datetime import datetime
from typing import Optional, Dict, AsyncGenerator

from arcor2.cached import UpdateableCachedProject
from arcor2.cached import UpdateableCachedScene


class Lock:

    SERVER_NAME = "SERVER"
    SCENE_NAME = "SCENE"
    PROJECT_NAME = "PROJECT"

    class Data:
        __slots__ = "owner", "timestamp", "count"

        def __init__(self, owner):
            self.owner = owner
            self.timestamp = datetime.now()
            self.count = 1

        def inc_count(self):
            self.count += 1
            self.timestamp = datetime.now()

        def dec_count(self):
            self.count -= 1
            self.timestamp = datetime.now()

    class LockedObject:
        __slots__ = "read", "write", "tree"

        def __init__(self):

            # object id: data
            self.read: Dict[str, "Lock.Data"] = {}
            self.write: Dict[str, "Lock.Data"] = {}
            self.tree: bool = False

        def read_lock(self, obj_id: str, owner: str) -> bool:

            if self.tree:
                return False

            if obj_id in self.write:
                return False

            already_locked = obj_id in self.read
            if already_locked and self.read[obj_id].owner != owner:
                return False

            if already_locked:
                self.read[obj_id].inc_count()
            else:
                self.read[obj_id] = Lock.Data(owner)

        def read_unlock(self, obj_id: str) -> bool:

            if obj_id not in self.read:
                return False

            if self.read[obj_id].count > 1:
                self.read[obj_id].dec_count()
            else:
                del self.read[obj_id]

            return True

        def write_lock(self, obj_id: str, owner: str, lock_tree: bool) -> bool:

            if self.tree:
                return False

            already_locked = obj_id in self.write
            if already_locked and self.write[obj_id].owner != owner:
                return False

            any_r_lock = next((True for r_lock in self.read.values() if r_lock.owner != owner), False)

            if lock_tree:
                any_w_lock = next((True for w_lock in self.write.values() if w_lock.owner != owner), False)
                if any_r_lock or any_w_lock:
                    return False
            else:
                if any_r_lock or obj_id in self.write:
                    return False

            if already_locked:
                self.write[obj_id].inc_count()
            else:
                self.write[obj_id] = Lock.Data(owner)
            self.tree = lock_tree
            return True

        def write_unlock(self, obj_id: str) -> bool:

            if obj_id not in self.write:
                return False

            self.write = None
            self.tree = False
            return True

        def is_empty(self) -> bool:

            return not self.read and not self.write

    def __init__(self):
        self.scene = None
        self.project = None

        self._lock = asyncio.Lock()
        self._locked_objects: Dict[str, "Lock.LockedObject"] = {}

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene: Optional["UpdateableCachedScene"] = None):

        assert self.project is None

        self._scene = scene

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, project: Optional["UpdateableCachedProject"] = None):

        assert self.scene is None

        self._project = project

    async def read_lock(self, obj_id: str, owner: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            locked = lock_record.read_lock(obj_id, owner)

            if not locked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return locked

    async def read_unlock(self, obj_id: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            unlocked = lock_record.read_unlock(obj_id)

            if unlocked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return unlocked

    async def write_lock(self, obj_id: str, owner: str, lock_tree: bool = False) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            locked = lock_record.write_lock(obj_id, owner, lock_tree)

            if not locked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return locked

    async def write_unlock(self, obj_id: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            lock_record = self._get_lock_record(root_id)
            unlocked = lock_record.write_unlock()

            if unlocked and lock_record.is_empty():
                del self._locked_objects[root_id]

        return unlocked

    async def is_write_locked(self, obj_id: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            return root_id in self._locked_objects and obj_id in self._locked_objects[root_id].write

    async def is_read_locked(self, obj_id: str) -> bool:

        root_id = self.get_root_id(obj_id)

        async with self._lock:
            return root_id in self._locked_objects and obj_id in self._locked_objects[root_id].read

    async def get_locked_roots_count(self) -> int:

        async with self._lock:
            return bool(self._locked_objects)

    def get_root_id(self, obj_id):
        """Retrieve root object id for given object"""

        if self.scene:
            # TODO scene object hierarchy
            return obj_id

        elif self.project:
            obj = self.project.action_point(obj_id)
            return obj.parent if obj.parent else obj_id

        elif obj_id in [self.SCENE_NAME, self.PROJECT_NAME]:
            return obj_id

        else:
            raise KeyError(f"Unknown object '{obj_id}'")

    def _get_lock_record(self, root_id: str) -> "Lock.LockedObject":
        """Create or retrieve lock record for root_id"""

        assert self._lock.locked()

        if root_id not in self._locked_objects:
            self._locked_objects[root_id] = Lock.LockedObject()

        return self._locked_objects[root_id]

    async def get_lock(self) -> AsyncGenerator[asyncio.Lock, None]:
        """
        Get lock for data structure
        Method should be used for operation with whole scene/project, no others
        """
        yield self._lock
