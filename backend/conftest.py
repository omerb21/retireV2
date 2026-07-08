from __future__ import annotations

import inspect

import httpx


_client_init = httpx.Client.__init__


def _client_init_compatible_with_starlette_testclient(self, *args, **kwargs):
    if "app" in kwargs and "app" not in inspect.signature(_client_init).parameters:
        kwargs.pop("app")

    return _client_init(self, *args, **kwargs)


httpx.Client.__init__ = _client_init_compatible_with_starlette_testclient
