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

import re

from clade import Clade


def test_ld(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("LD")

    cmds = list(e.load_all_cmds(with_opts=True, with_raw=True))

    target_cmd = dict()

    for cmd in cmds:
        for cmd_out in cmd["out"]:
            if re.search("main.o2", cmd_out):
                target_cmd = cmd

    assert len(cmds) >= 1
    assert len(target_cmd["in"]) == 2
    assert len(target_cmd["out"]) == 1
    assert len(target_cmd["opts"]) == 7
    assert len(target_cmd["command"]) == 11
