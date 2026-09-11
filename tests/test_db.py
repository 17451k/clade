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

import os

import pytest

from clade.db import Database, buffered


@pytest.fixture
def db(tmpdir):
    return Database(os.path.join(str(tmpdir), "clade.db"))


def test_missing(db):
    assert db.get("CC", "cmds", "1") is None
    assert not db.has("CC", "cmds", "1")
    assert list(db.iter("CC", "cmds")) == []
    # Reads must not create the database
    assert not db.exists()


def test_put_get(db):
    db.put("CC", "cmds", "1", {"id": 1, "in": ["main.c"]})
    db.put("CC", "cmds.json", "", [1, 2, 3])

    assert db.get("CC", "cmds", "1") == {"id": 1, "in": ["main.c"]}
    assert db.get("CC", "cmds.json") == [1, 2, 3]
    assert db.has("CC", "cmds", "1")
    assert not db.has("LD", "cmds", "1")

    # Same key is replaced
    db.put("CC", "cmds", "1", {"id": 1})
    assert db.get("CC", "cmds", "1") == {"id": 1}


def test_iter(db):
    data = {str(i): {"id": i} for i in range(1200)}
    db.put_many("CC", "cmds", data)

    assert dict(db.iter("CC", "cmds")) == data
    # More keys than fit in one IN (...) clause
    keys = [str(i) for i in range(0, 1200, 2)]
    assert dict(db.iter("CC", "cmds", keys)) == {k: data[k] for k in keys}
    assert dict(db.iter("CC", "cmds", ["1", "missing"])) == {"1": {"id": 1}}


def test_delete(db):
    db.put("CC", "cmds", "1", {})
    db.put("LD", "cmds", "1", {})
    db.delete("CC")

    assert not db.has("CC", "cmds", "1")
    assert db.has("LD", "cmds", "1")


def test_transaction_rollback(db):
    db.put("CC", "cmds", "1", {})

    with pytest.raises(RuntimeError), db.transaction():
        db.put("CC", "cmds", "2", {})
        raise RuntimeError

    assert db.has("CC", "cmds", "1")
    assert not db.has("CC", "cmds", "2")


def test_buffered(db):
    with buffered() as rows:
        db.put("CC", "cmds", "1", {"id": 1})
        assert not db.exists()

    assert len(rows) == 1
    db.put_rows(rows)
    assert db.get("CC", "cmds", "1") == {"id": 1}


def test_close_reopens(db):
    db.put("CC", "cmds", "1", {})
    db.close()
    os.remove(db.path)

    assert not db.exists()
    db.put("CC", "cmds", "2", {})
    assert not db.has("CC", "cmds", "1")
    assert db.has("CC", "cmds", "2")


def test_compress(tmpdir):
    plain = Database(os.path.join(str(tmpdir), "clade.db"))
    plain.put("CC", "cmds", "1", {"id": 1})
    assert isinstance(plain.conn.execute("SELECT value FROM data").fetchone()[0], str)

    packed = Database(os.path.join(str(tmpdir), "clade.db"), compress=True)
    packed.put("CC", "cmds", "2", {"id": 2})
    assert isinstance(
        packed.conn.execute("SELECT value FROM data WHERE key = '2'").fetchone()[0],
        bytes,
    )

    # Both encodings are read back transparently
    assert dict(plain.iter("CC", "cmds")) == {"1": {"id": 1}, "2": {"id": 2}}

    plain.recode(compress=True)
    assert all(
        isinstance(v, bytes) for (v,) in plain.conn.execute("SELECT value FROM data")
    )
    plain.recode(compress=False)
    assert all(
        isinstance(v, str) for (v,) in plain.conn.execute("SELECT value FROM data")
    )
    assert dict(plain.iter("CC", "cmds")) == {"1": {"id": 1}, "2": {"id": 2}}
