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

from clade.extensions.ld import LD


def test_ld(tmpdir, cmds_file):
    c = LD(tmpdir)
    c.parse(cmds_file)

    cmds = c.load_all_cmds()

    target_cmd = dict()

    for cmd in cmds:
        for cmd_out in cmd["out"]:
            if re.search("main.o2", cmd_out):
                target_cmd = cmd

    assert len(cmds) >= 1
    assert len(target_cmd["in"]) == 1
    assert len(target_cmd["out"]) == 1
    assert len(target_cmd["opts"]) == 1
