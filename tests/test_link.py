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
import pathlib

import pytest

from clade.cmds import Cmd
from clade.extensions.link import Link


def get_cmd(tmp_path, command) -> Cmd:
    return {
        "cwd": str(tmp_path),
        "pid": 0,
        "id": 1,
        "which": "/usr/bin/link",
        "command": command,
    }


def test_link_simple(tmp_path: pathlib.Path):
    link = Link(tmp_path)

    cmd = get_cmd(tmp_path, ["link", "/OUT:a.exe", "/NOLOGO", "main.obj", "zero.obj"])

    result = link.parse_cmd(cmd)
    assert result is None

    parsed_cmd = link.load_cmd_by_id(1)

    assert parsed_cmd["out"] == ["a.exe"]
    assert parsed_cmd["in"] == ["main.obj", "zero.obj"]
    assert link.load_opts_by_id(1) == ["/NOLOGO"]


@pytest.mark.parametrize("libpath_opt", ["/libpath:", "/LIBPATH:", "-LibPath:"])
def test_link_libpath_existing(tmp_path: pathlib.Path, libpath_opt):
    link = Link(tmp_path)

    libdir = tmp_path / "libdir"
    libdir.mkdir()
    libfile = libdir / "foo.lib"
    with open(libfile, "w"):
        pass

    cmd = get_cmd(
        tmp_path,
        ["link", "-out:b.exe", f"{libpath_opt}{libdir}", "foo.lib"],
    )

    result = link.parse_cmd(cmd)
    assert result is None

    parsed_cmd = link.load_cmd_by_id(1)

    assert parsed_cmd["out"] == ["b.exe"]
    assert parsed_cmd["in"] == [os.path.join(str(libdir), "foo.lib")]
    assert link.load_opts_by_id(1) == [f"{libpath_opt}{libdir}"]


def test_link_libpath_missing(tmp_path: pathlib.Path):
    link = Link(tmp_path)

    libdir = tmp_path / "libdir"
    libdir.mkdir()

    cmd = get_cmd(
        tmp_path,
        ["link", "-out:b.exe", f"/libpath:{libdir}", "foo.lib"],
    )

    result = link.parse_cmd(cmd)
    assert result is None

    parsed_cmd = link.load_cmd_by_id(1)

    assert parsed_cmd["out"] == ["b.exe"]
    assert parsed_cmd["in"] == ["foo.lib"]
    assert link.load_opts_by_id(1) == [f"/libpath:{libdir}"]
