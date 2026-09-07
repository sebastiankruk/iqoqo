# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Cache configuration."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from flask_caching import Cache

_local_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_local_lock(name: str) -> threading.Lock:
    with _locks_guard:
        if name not in _local_locks:
            _local_locks[name] = threading.Lock()
        return _local_locks[name]


class AppCache(Cache):
    """Custom Cache class with distributed/local lock support."""

    @contextmanager
    def lock(self, name: str, timeout: int = 30) -> Iterator[None]:
        """Acquire a distributed lock via Redis if available, else fallback to a local lock."""
        client = None
        try:
            backend = getattr(self, "cache", None)
            client = getattr(backend, "_client", None)
        except (AttributeError, RuntimeError):
            client = None

        if client and hasattr(client, "lock"):
            with client.lock(name, timeout=timeout):
                yield
        else:
            with _get_local_lock(name):
                yield


cache = AppCache(config={"CACHE_TYPE": "SimpleCache"})  # Default to memory, but app init will override with Redis
