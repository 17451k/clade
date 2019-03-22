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

import os

from clade.extensions.src_graph import SrcGraph
from clade.extensions.path import Path

test_file_rel = "tests/test_project/main.c"
test_file_abs = os.path.abspath(test_file_rel)


def test_path(tmpdir, cmds_file):
    c = SrcGraph(tmpdir)
    c.parse(cmds_file)

    p = Path(tmpdir)

    assert p.get_abs_path(test_file_abs) == test_file_abs
    assert p.normalize_rel_path(test_file_rel, os.getcwd()) == test_file_abs
