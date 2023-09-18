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
from clade.cmds import get_last_id


def test_pid_graph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("PidGraph")

    last_id = get_last_id(cmds_file)

    pid_graph = e.load_pid_graph()
    pid_by_id = e.load_pid_by_id()

    cmd_ids = list(x for x in range(1, int(last_id) + 1))
    assert len(pid_graph) == len(cmd_ids)

    for cmd_id in cmd_ids:
        assert cmd_id in pid_graph
        assert len(pid_graph[cmd_id]) >= 1

        for pid in pid_graph[cmd_id]:
            assert int(pid) < int(cmd_id)

    assert len(pid_by_id) == len(cmd_ids)

    for cmd_id in cmd_ids:
        assert cmd_id in pid_by_id
        assert int(pid_by_id[cmd_id]) < int(cmd_id)
