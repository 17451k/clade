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

import pathlib
import sys

import pytest

from clade import Clade
from clade.cmds import Cmd
from clade.extensions.objcopy import Objcopy


@pytest.mark.skipif(sys.platform != "linux", reason="test only for Linux")
def test_objcopy(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("Objcopy")

    cmds = e.load_all_cmds(with_opts=True, with_raw=True)
    assert len(cmds) == 2
    for cmd in cmds:
        assert len(cmd["in"]) == 1
        assert len(cmd["out"]) == 1
        assert len(cmd["opts"]) == 1


def get_cmd(tmp_path, command) -> Cmd:
    return {
        "cwd": str(tmp_path),
        "pid": 0,
        "id": 1,
        "which": "/usr/bin/objcopy",
        "command": command,
    }


def test_objcopy_single_file(tmp_path: pathlib.Path):
    e = Objcopy(tmp_path)

    cmd = get_cmd(tmp_path, ["objcopy", "--strip-all", "main.o"])
    e.parse_cmd(cmd)

    parsed_cmd = e.load_cmd_by_id(1)
    assert parsed_cmd["in"] == ["main.o"]
    assert parsed_cmd["out"] == ["main.o"]
    assert e.load_opts_by_id(1) == ["--strip-all"]


def test_objcopy_in_out(tmp_path: pathlib.Path):
    e = Objcopy(tmp_path)

    cmd = get_cmd(tmp_path, ["objcopy", "main.o", "zero.o", "--strip-all"])
    e.parse_cmd(cmd)

    parsed_cmd = e.load_cmd_by_id(1)
    assert parsed_cmd["in"] == ["main.o"]
    assert parsed_cmd["out"] == ["zero.o"]
