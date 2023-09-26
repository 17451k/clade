# Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
# Ivannikov Institute for System Programming of the Russian Academy of Sciences
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

from clade import Clade
from clade.scripts.compilation_database import main


@pytest.mark.parametrize("filter_opts", [True, False])
def test_cdb(tmpdir, cmds_file, filter_opts):
    cdb_json = os.path.join(str(tmpdir), "cdb.json")

    c = Clade(
        tmpdir, cmds_file, conf={"CDB.output": cdb_json, "CDB.filter_opts": filter_opts}
    )
    e = c.parse("CDB")

    cdb = e.load_cdb()
    assert cdb

    cc = c.parse("CC")
    assert len(cdb) >= len(list(cc.load_all_cmds()))

    for cmd in cdb:
        assert "directory" in cmd
        assert "arguments" in cmd
        assert "file" in cmd

        for arg in cmd["arguments"]:
            assert isinstance(arg, str)

        if filter_opts:
            assert "-fsyntax-only" not in cmd["arguments"]


def test_cdb_main(tmpdir, cmds_file):
    main(["-o", os.path.join(str(tmpdir), "cdb.json"), "--cmds", cmds_file])
