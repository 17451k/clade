# Copyright (c) 2026 Ilya Shchepetkov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
import sqlite3
import threading
import zlib
from collections.abc import Generator, Iterable
from typing import Any

import orjson

from clade.utils import array_hook

Row = tuple[str, str, str, str | bytes]

# One connection per (path, process, thread):
# - sqlite connections must not be shared across fork() or threads
# - extension objects are pickled into worker processes
_connections: dict[tuple[str, int, int], sqlite3.Connection] = {}

# While set, writes are collected here instead of going to the database.
# Worker processes run with it enabled and hand the rows back to the parent,
# which is the only process that writes
_buffer: list[Row] | None = None

# A rowid table: WITHOUT ROWID keeps only a quarter of a page in-leaf, so the
# multi-kilobyte values overflow and the file gets 50% bigger
_SCHEMA = """
CREATE TABLE IF NOT EXISTS data (
    ext TEXT NOT NULL,
    name TEXT NOT NULL,
    key TEXT NOT NULL,
    value BLOB NOT NULL,
    PRIMARY KEY (ext, name, key)
)
"""

_PRAGMAS = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA cache_size = -8192",
]

# Bound by SQLITE_MAX_VARIABLE_NUMBER
_CHUNK = 500


def encode(data: Any, compress: bool = False) -> str | bytes:
    """JSON text, or a zlib blob when compression is on.

    Level 1 already shrinks the JSON about 4x; higher levels cost several
    times more CPU for a few percent.
    """
    encoded = orjson.dumps(data, default=array_hook)

    return zlib.compress(encoded, 1) if compress else encoded.decode()


def decode(value: str | bytes) -> Any:
    # SQLite hands TEXT back as str and BLOB as bytes, so a database may
    # even mix both encodings
    return orjson.loads(zlib.decompress(value) if isinstance(value, bytes) else value)


@contextlib.contextmanager
def buffered() -> Generator[list[Row], None, None]:
    global _buffer

    outer = _buffer
    _buffer = rows = []
    try:
        yield rows
    finally:
        _buffer = outer


class Database:
    def __init__(self, path: str, compress: bool = False):
        self.path = path
        self.compress = compress
        self._depth = 0
        self._exists = False

    def __getstate__(self):
        return {
            "path": self.path,
            "compress": self.compress,
            "_depth": 0,
            "_exists": False,
        }

    @property
    def conn(self) -> sqlite3.Connection:
        key = (self.path, os.getpid(), threading.get_ident())

        if key not in _connections:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            conn = sqlite3.connect(self.path, isolation_level=None, timeout=300)
            for pragma in _PRAGMAS:
                conn.execute(pragma)
            conn.execute(_SCHEMA)
            _connections[key] = conn

        return _connections[key]

    def close(self) -> None:
        """Forget this process's connections, e.g. before the file is removed."""
        for key in [k for k in _connections if k[0] == self.path]:
            if key[2] == threading.get_ident():
                _connections[key].close()
            del _connections[key]

        self._exists = False

    def exists(self) -> bool:
        # Once created the file stays, so the check is only repeated until then
        if not self._exists:
            self._exists = os.path.exists(self.path)

        return self._exists

    @contextlib.contextmanager
    def transaction(self) -> Generator[None, None, None]:
        if self._depth == 0:
            self.conn.execute("BEGIN")
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("ROLLBACK")
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("COMMIT")

    def put(self, ext: str, name: str, key: str, data: Any) -> None:
        self.put_rows([(ext, name, key, encode(data, self.compress))])

    def put_many(self, ext: str, name: str, data: dict[str, Any]) -> None:
        self.put_rows(
            (ext, name, key, encode(value, self.compress))
            for key, value in data.items()
        )

    def put_rows(self, rows: Iterable[Row]) -> None:
        if _buffer is not None:
            _buffer.extend(rows)
            return

        with self.transaction():
            self.conn.executemany(
                "INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)", rows
            )

    def get(self, ext: str, name: str, key: str = "") -> Any:
        if not self.exists():
            return None

        row = self.conn.execute(
            "SELECT value FROM data WHERE ext = ? AND name = ? AND key = ?",
            (ext, name, key),
        ).fetchone()

        return decode(row[0]) if row else None

    def has(self, ext: str, name: str, key: str = "") -> bool:
        if not self.exists():
            return False

        return (
            self.conn.execute(
                "SELECT 1 FROM data WHERE ext = ? AND name = ? AND key = ?",
                (ext, name, key),
            ).fetchone()
            is not None
        )

    def iter(
        self, ext: str, name: str, keys: Iterable[str] | None = None
    ) -> Generator[tuple[str, Any], None, None]:
        if not self.exists():
            return

        if keys is None:
            cursor = self.conn.execute(
                "SELECT key, value FROM data WHERE ext = ? AND name = ?", (ext, name)
            )
            for key, value in cursor:
                yield key, decode(value)
            return

        keys = list(keys)
        for i in range(0, len(keys), _CHUNK):
            chunk = keys[i : i + _CHUNK]
            cursor = self.conn.execute(
                "SELECT key, value FROM data WHERE ext = ? AND name = ? AND key IN ({})".format(
                    ",".join("?" * len(chunk))
                ),
                (ext, name, *chunk),
            )
            for key, value in cursor:
                yield key, decode(value)

    def recode(self, compress: bool) -> None:
        """Rewrite every value as text or as a zlib blob, then reclaim the space."""
        with self.transaction():
            cursor = self.conn.execute("SELECT rowid, value FROM data")
            for rowid, value in cursor.fetchall():
                if isinstance(value, bytes) != compress:
                    self.conn.execute(
                        "UPDATE data SET value = ? WHERE rowid = ?",
                        (encode(decode(value), compress), rowid),
                    )

        self.conn.execute("VACUUM")

    def delete(self, ext: str) -> None:
        if not self.exists():
            return

        with self.transaction():
            self.conn.execute("DELETE FROM data WHERE ext = ?", (ext,))
