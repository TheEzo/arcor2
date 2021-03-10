from websockets.server import WebSocketServerProtocol as WsClient

from arcor2.exceptions import Arcor2Exception
from arcor2_arserver import globals as glob
from arcor2_arserver_data import rpc as srpc


async def write_lock_cb(req: srpc.lock.WriteLock.Request, ui: WsClient) -> None:

    assert glob.LOCK

    if await glob.LOCK.write_lock(req.args.obj_id, 'ui.owner TBD', req.args.lock_tree):
        ...  # TODO notify
    else:
        raise Arcor2Exception('Object locking failed.')


async def write_unlock_cb(req: srpc.lock.WriteUnlock.Request, ui: WsClient) -> None:

    assert glob.LOCK

    await glob.LOCK.write_unlock(req.args.obj_id, 'owner')
    # TODO notify


async def read_lock_cb(req: srpc.lock.ReadLock.Request, ui: WsClient) -> None:

    assert glob.LOCK

    if await glob.LOCK.read_lock(req.args.obj_id, 'ui.owner TBD'):
        ...  # TODO notify
    else:
        raise Arcor2Exception('Object locking failed')


async def read_unlock_cb(req: srpc.lock.ReadUnlock.Request, ui: WsClient) -> None:

    assert glob.LOCK

    await glob.LOCK.read_unlock(req.args.obj_id, 'owner')
    # TODO notify
