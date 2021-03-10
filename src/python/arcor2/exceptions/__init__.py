class Arcor2Exception(Exception):
    """All exceptions are derived from this one."""

    pass


class Arcor2NotImplemented(Arcor2Exception):
    pass


class CannotUnlock(Arcor2Exception):
    pass


class CannotLock(Arcor2Exception):
    pass
