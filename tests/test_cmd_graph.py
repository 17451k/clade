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

from clade.extensions.cmd_graph import CmdGraph


def test_cmd_graph_requires(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = CmdGraph(tmpdir, conf)
    c.parse(cmds_file)

    cmd_graph = c.load_cmd_graph()

    cmd_id = None
    for cmd in c.extensions["CC"].load_all_cmds():
        if "main.c" in cmd["in"] and "zero.c" in cmd["in"] and "tmp_main" in cmd["out"]:
            cmd_id = str(cmd["id"])

    assert cmd_id
    assert cmd_graph
    assert cmd_graph[cmd_id]["type"] == "CC"
    assert len(cmd_graph[cmd_id]["used_by"]) == 1
    assert cmd_graph[cmd_id]["using"] == []

    used_by_id = cmd_graph[cmd_id]["used_by"][0]
    assert cmd_graph[used_by_id]["using"] == [cmd_id]


def test_cmd_graph_empty_requires(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": []}

    c = CmdGraph(tmpdir, conf)
    c.parse(cmds_file)

    cmd_graph = c.load_cmd_graph()
    assert not cmd_graph


@pytest.mark.parametrize("as_picture", [True, False])
def test_cmd_graph_as_picture(tmpdir, cmds_file, as_picture):
    conf = {"CmdGraph.as_picture": as_picture}

    c = CmdGraph(tmpdir, conf)
    c.parse(cmds_file)

    assert os.path.exists(c.graph_dot) == as_picture
    assert os.path.exists(c.graph_dot + ".pdf") == as_picture


def test_cmd_graph_empty_conf(tmpdir, cmds_file):
    c = CmdGraph(tmpdir)
    c.parse(cmds_file)

    assert c.load_cmd_graph()
