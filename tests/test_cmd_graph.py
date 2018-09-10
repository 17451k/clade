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

from clade.extensions.cmd_graph import CmdGraph


def test_cmd_graph_requires(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = CmdGraph(tmpdir, conf)
    c.parse(cmds_file)

    cmd_graph = c.load_cmd_graph()

    assert cmd_graph
    assert cmd_graph["2"]["type"] == "CC"
    assert cmd_graph["2"]["used_by"] == ["3"]
    assert cmd_graph["2"]["using"] == []
    assert cmd_graph["3"]["using"] == ["2"]


def test_cmd_graph_empty_requires(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": []}

    c = CmdGraph(tmpdir, conf)
    c.parse(cmds_file)

    cmd_graph = c.load_cmd_graph()
    assert not cmd_graph


def test_cmd_graph_as_picture(tmpdir, cmds_file):
    conf = {"CmdGraph.as_picture": True}

    c = CmdGraph(tmpdir, conf)
    c.parse(cmds_file)

    assert os.path.exists(os.path.join(c.work_dir, "cmd_graph.dot.pdf"))


def test_cmd_graph_empty_conf(tmpdir, cmds_file):
    c = CmdGraph(tmpdir)
    c.parse(cmds_file)

    assert c.load_cmd_graph()
