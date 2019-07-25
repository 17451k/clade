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

from clade.main import main

test_project = os.path.join(os.path.dirname(__file__), "test_project")
test_project_make = ["make", "-C", test_project]


def test_intercept(tmpdir):
    cmds_file = os.path.join(str(tmpdir), "cmds.txt")

    with pytest.raises(SystemExit) as excinfo:
        main(["--cmds", cmds_file, "-i"] + test_project_make)

    assert "0" == str(excinfo.value)


def test_intercept_no_command():
    with pytest.raises(SystemExit) as excinfo:
        main(["-i"])

    assert "-1" == str(excinfo.value)
