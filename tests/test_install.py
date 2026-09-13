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

from clade.cmds import Cmd
from clade.extensions.install import Install


def create_empty_file(path):
    with open(path, "w"):
        pass

    return path


def get_cmd(tmp_path, command) -> Cmd:
    return {
        "cwd": str(tmp_path),
        "pid": 0,
        "id": 1,
        "which": "/usr/bin/install",
        "command": command.split(" "),
    }


def test_install_mode(tmp_path: pathlib.Path):
    install = Install(tmp_path)

    in_file = create_empty_file(tmp_path / "test.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"install -m 644 {in_file} {out_dir}")

    parsed = install.parse_cmd(cmd)

    assert parsed
    assert parsed["in"] == [os.path.normpath(str(in_file))]
    assert parsed["out"] == [
        os.path.normpath(os.path.join(str(out_dir), os.path.basename(str(in_file))))
    ]
    assert install.load_opts_by_id(cmd["id"]) == ["-m", "644"]


def test_install_target_directory_short(tmp_path: pathlib.Path):
    install = Install(tmp_path)

    in_file1 = create_empty_file(tmp_path / "f1.txt")
    in_file2 = create_empty_file(tmp_path / "f2.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"install -t {out_dir} {in_file1} {in_file2}")

    parsed = install.parse_cmd(cmd)

    assert parsed
    assert parsed["in"] == [
        os.path.normpath(str(in_file1)),
        os.path.normpath(str(in_file2)),
    ]
    assert parsed["out"] == [
        os.path.normpath(os.path.join(str(out_dir), os.path.basename(str(in_file1)))),
        os.path.normpath(os.path.join(str(out_dir), os.path.basename(str(in_file2)))),
    ]


def test_install_target_directory_long(tmp_path: pathlib.Path):
    install = Install(tmp_path)

    in_file1 = create_empty_file(tmp_path / "f1.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"install --target-directory={out_dir} {in_file1}")

    parsed = install.parse_cmd(cmd)

    assert parsed
    assert parsed["out"] == [
        os.path.normpath(os.path.join(str(out_dir), os.path.basename(str(in_file1))))
    ]


def test_install_explicit_out_file(tmp_path: pathlib.Path):
    # Commands are parsed after they ran, so the output file already exists
    install = Install(tmp_path)

    in_file1 = create_empty_file(tmp_path / "f1.txt")
    out_file = create_empty_file(tmp_path / "f2.txt")

    cmd = get_cmd(tmp_path, f"install {in_file1} {out_file}")

    parsed_cmd = install.parse_cmd(cmd)

    assert parsed_cmd
    assert parsed_cmd["in"] == [os.path.normpath(in_file1)]
    assert parsed_cmd["out"] == [os.path.normpath(out_file)]


def test_install_nonexistent_input(tmp_path: pathlib.Path):
    install = Install(tmp_path)

    nonexistent_file = tmp_path / "does_not_exist.txt"
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"install {nonexistent_file} {out_dir}")

    assert install.parse_cmd(cmd) is None
