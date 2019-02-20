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

import sys

from clade.extensions.objcopy import Objcopy


def test_objcopy(tmpdir, cmds_file):
    if not sys.platform == "linux":
        return

    c = Objcopy(tmpdir)
    c.parse(cmds_file)

    cmds = c.load_all_cmds(with_opts=True, with_raw=True)
    assert len(cmds) == 2
    for cmd in cmds:
        assert len(cmd["in"]) == 1
        assert len(cmd["out"]) == 1
        assert len(cmd["opts"]) == 1
