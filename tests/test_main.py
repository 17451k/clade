# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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

import pytest
import os
import sys

from clade.__main__ import main

test_project = os.path.join(os.path.dirname(__file__), "test_project")
test_project_make = ["make", "-C", test_project]


@pytest.mark.skipif(sys.platform == "darwin", reason="test doesn't work on macOS")
def test_intercept(tmpdir):
    cmds_file = os.path.join(str(tmpdir), "cmds.txt")

    with pytest.raises(SystemExit) as e:
        main(["--cmds", cmds_file, "-i"] + test_project_make)

    assert "0" == str(e.value)


def test_intercept_no_command():
    with pytest.raises(SystemExit) as e:
        main(["-i"])

    assert "-1" == str(e.value)


def test_main_cc(tmpdir, cmds_file):
    with pytest.raises(SystemExit) as e:
        main(["-w", str(tmpdir), "--cmds", cmds_file, "-e", "CC"])

    assert "0" == str(e.value)


def test_main_bad_conf(tmpdir, cmds_file):
    with pytest.raises(SystemExit) as e:
        main(["-w", str(tmpdir), "--cmds", cmds_file, "-c", "does_not_exist.conf"])

    assert "-1" == str(e.value)


def test_main_bad_preset(tmpdir, cmds_file):
    with pytest.raises(SystemExit):
        main(["-w", str(tmpdir), "--cmds", cmds_file, "-p", "does_not_exist"])


def test_main_good_json(tmpdir, cmds_file):
    with pytest.raises(SystemExit) as e:
        main(
            [
                "-w",
                str(tmpdir),
                "--cmds",
                cmds_file,
                "-e",
                "PidGraph",
                "--conf",
                '{"CmdGraph.requires": []}',
            ]
        )

    assert "0" == str(e.value)


def test_main_bad_json(tmpdir, cmds_file):
    with pytest.raises(SystemExit) as e:
        main(
            [
                "-w",
                str(tmpdir),
                "--cmds",
                cmds_file,
                "-e",
                "PidGraph",
                "--conf",
                '{"CmdGraph.requires": [}',
            ]
        )

    assert "-1" == str(e.value)
