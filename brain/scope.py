"""Per-request data root for demo sessions. Unset until a demo request binds one."""

import contextvars
from pathlib import Path

_root = contextvars.ContextVar("sino_data_root", default=None)
_hub = contextvars.ContextVar("sino_hub", default=None)
_session = contextvars.ContextVar("sino_session", default=None)


def current_root():
    value = _root.get()
    if not value:
        return None
    return Path(value)


def current_hub():
    return _hub.get()


def current_session():
    return _session.get()


def push_root(root):
    return _root.set(str(root))


def pop_root(token):
    _root.reset(token)


def bind(root, hub, session):
    return (_root.set(str(root)), _hub.set(hub), _session.set(session))


def unbind(tokens):
    _root.reset(tokens[0])
    _hub.reset(tokens[1])
    _session.reset(tokens[2])
