# Copyright (c) 2022 Ilya Shchepetkov
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
import subprocess
import pathlib

from clade.extensions.ln import LN


def get_cmd(tmp_path, command):
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    subprocess.run(command, cwd=cwd, shell=True)

    return {
        "cwd": str(cwd),
        "pid": "0",
        "id": "1",
        "which": "/usr/bin/ln",
        "command": command.split(" "),
    }


def create_empty_file(path):
    with open(path, "w"):
        pass

    return path


def check_ln(parsed_cmd):
    assert len(parsed_cmd["in"]) == len(parsed_cmd["out"])

    for i, cmd_in in enumerate(parsed_cmd["in"]):
        assert os.path.basename(cmd_in) == os.path.basename(parsed_cmd["out"][i])


def test_ln_cwd(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file = create_empty_file(tmp_path / "test.txt")
    cmd = get_cmd(tmp_path, f"ln {in_file}")

    parsed_cmd = ln.parse_cmd(cmd)

    assert parsed_cmd
    assert len(parsed_cmd["in"]) == len(parsed_cmd["out"])
    assert len(parsed_cmd["in"]) == 1
    assert os.path.basename(parsed_cmd["in"][0]) == os.path.basename(in_file)
    assert os.path.basename(parsed_cmd["out"][0]) == os.path.basename(in_file)
    assert cmd["cwd"] in parsed_cmd["out"][0]


def test_ln_single(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file = create_empty_file(tmp_path / "test1.txt")
    out_file = tmp_path / "test2.txt"
    cmd = get_cmd(tmp_path, f"ln {in_file} {out_file}")

    parsed_cmd = ln.parse_cmd(cmd)

    assert parsed_cmd
    assert len(parsed_cmd["in"]) == len(parsed_cmd["out"])
    assert len(parsed_cmd["in"]) == 1
    assert os.path.basename(parsed_cmd["in"][0]) == os.path.basename(in_file)
    assert os.path.basename(parsed_cmd["out"][0]) == os.path.basename(out_file)


def test_ln_multiple(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file1 = create_empty_file(tmp_path / "test1.txt")
    in_file2 = create_empty_file(tmp_path / "test2.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"ln {in_file1} {in_file2} {out_dir}")

    parsed_cmd = ln.parse_cmd(cmd)

    assert parsed_cmd
    assert len(parsed_cmd["in"]) == len(parsed_cmd["out"])
    assert len(parsed_cmd["in"]) == 2
    assert os.path.basename(parsed_cmd["in"][0]) == os.path.basename(in_file1)
    assert os.path.basename(parsed_cmd["in"][1]) == os.path.basename(in_file2)
    assert os.path.basename(parsed_cmd["out"][0]) == os.path.basename(in_file1)
    assert os.path.basename(parsed_cmd["out"][1]) == os.path.basename(in_file2)
    assert str(out_dir) in parsed_cmd["out"][0]
    assert str(out_dir) in parsed_cmd["out"][1]


def check_target(parsed_cmd, in_file, out_dir):
    assert parsed_cmd
    assert len(parsed_cmd["in"]) == len(parsed_cmd["out"])
    assert len(parsed_cmd["in"]) == 1
    assert os.path.basename(parsed_cmd["in"][0]) == os.path.basename(in_file)
    assert os.path.basename(parsed_cmd["out"][0]) == os.path.basename(in_file)
    assert str(out_dir) in parsed_cmd["out"][0]


def test_ln_t1(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file = create_empty_file(tmp_path / "test.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"ln -t {out_dir} {in_file}")

    parsed_cmd = ln.parse_cmd(cmd)
    check_target(parsed_cmd, in_file, out_dir)


def test_ln_t2(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file = create_empty_file(tmp_path / "test.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"ln -t{out_dir} {in_file}")

    parsed_cmd = ln.parse_cmd(cmd)
    check_target(parsed_cmd, in_file, out_dir)


def test_ln_target1(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file = create_empty_file(tmp_path / "test.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"ln --target-directory={out_dir} {in_file}")

    parsed_cmd = ln.parse_cmd(cmd)
    check_target(parsed_cmd, in_file, out_dir)


def test_ln_target2(tmp_path: pathlib.Path):
    ln = LN(tmp_path)

    in_file = create_empty_file(tmp_path / "test.txt")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    cmd = get_cmd(tmp_path, f"ln --target-directory {out_dir} {in_file}")

    parsed_cmd = ln.parse_cmd(cmd)
    check_target(parsed_cmd, in_file, out_dir)
