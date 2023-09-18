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
import shutil

from clade import Clade
from tests.test_project import main_c, zero_c, tmp_main


def test_cmd_graph_requires(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CmdGraph")

    cmd_graph = e.load_cmd_graph()
    cmd_type = e.load_cmd_type()

    cmd_id = None
    for cmd in e.extensions["CC"].load_all_cmds():
        if main_c in cmd["in"] and zero_c in cmd["in"] and tmp_main in cmd["out"]:
            cmd_id = cmd["id"]

    assert cmd_id
    assert cmd_graph
    assert cmd_type[cmd_id] == "CC"
    assert len(cmd_graph[cmd_id]["used_by"]) == 1
    assert cmd_graph[cmd_id]["using"] == []

    used_by_id = cmd_graph[cmd_id]["used_by"][0]
    assert cmd_graph[used_by_id]["using"] == [cmd_id]


def test_cmd_graph_empty_requires(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": []}

    c = Clade(tmpdir, cmds_file, conf)

    with pytest.raises(RuntimeError):
        c.parse("CmdGraph")


@pytest.mark.parametrize("as_picture", [True, False])
@pytest.mark.skipif(not shutil.which("dot"), reason="dot is not installed")
def test_cmd_graph_as_picture(tmpdir, cmds_file, as_picture):
    conf = {"CmdGraph.as_picture": as_picture}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CmdGraph")

    assert os.path.exists(e.pdf_file + ".pdf") == as_picture


def test_cmd_graph_empty_conf(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("CmdGraph")

    assert e.load_cmd_graph()
