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

from clade import Clade
from clade.cmds import Cmd
from clade.extensions.ar import AR


def test_ar_bad_cmd(tmp_path):
    cmd: Cmd = {
        "cwd": str(tmp_path),
        "pid": 0,
        "id": 1,
        "which": "/usr/bin/ar",
        "command": ["ar", "rcs"],
    }
    e = AR(tmp_path)
    assert e.parse_cmd(cmd) is None
    assert e.get_bad_ids() == [1]


def test_ar(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("AR")

    cmds = e.load_all_cmds(with_opts=True, with_raw=True)
    assert len(cmds) == 1
    assert len(cmds[0]["in"]) == 2
    assert len(cmds[0]["out"]) == 1
    assert len(cmds[0]["opts"]) == 1
    assert len(cmds[0]["command"]) == 5
