# Copyright (c) 2021 ISP RAS (http://www.ispras.ru)
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
import sys

from clade import Clade

test_build = ["pip", "install", "--user", "--no-binary", ":all:", "--force", "cchardet"]


@pytest.mark.skipif(sys.platform != "win32", reason="tests only for Windows")
def test_windows(tmpdir):
    work_dir = os.path.join(str(tmpdir), "clade")
    output = os.path.join(str(tmpdir), "cmds.txt")

    c = Clade(work_dir, cmds_file=output)

    assert not c.intercept(command=test_build)

    c.parse("SrcGraph")

    assert c.pid_graph
    assert c.cmds
    assert c.cmd_graph
    assert c.src_graph
