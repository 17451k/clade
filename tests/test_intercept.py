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

from clade.intercept import Interceptor, main


test_project = os.path.join(os.path.dirname(__file__), "test_project")
test_project_make = ["make", "-C", test_project]


def calculate_loc(file):
    with open(file, "rb") as f:
        for i, _ in enumerate(f):
            pass
    return i + 1


def test_no_fallback(tmpdir):
    output = os.path.join(str(tmpdir), "cmds.txt")

    i = Interceptor(command=test_project_make, output=output, fallback=False)
    i.execute()

    assert not i.execute()
    assert os.path.isfile(output)

    # Do not check size of output file since LD_PRELOAD may not work on certain systems
    # Due to SELinux or System Integrity Protection
    # assert calculate_loc(output) > 1


def test_fallback(tmpdir):
    output = os.path.join(str(tmpdir), "cmds.txt")

    i = Interceptor(command=test_project_make, output=output, fallback=True)
    i.execute()

    assert not i.execute()
    assert os.path.isfile(output)
    assert calculate_loc(output) > 1


def test_main(tmpdir):
    output = os.path.join(str(tmpdir), "cmds.txt")

    with pytest.raises(SystemExit) as excinfo:
        main(["-o", output] + test_project_make)

    assert "0" in str(excinfo.value)


def test_main_no_args():
    with pytest.raises(SystemExit) as excinfo:
        main([])

    assert "0" not in str(excinfo.value)
