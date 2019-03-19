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

from clade.extensions.src_graph import SrcGraph

test_file = os.path.abspath("tests/test_project/main.c")


def test_src_graph(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = SrcGraph(tmpdir, conf)
    c.parse(cmds_file)

    src_graph = c.load_src_graph()

    assert src_graph
    assert len(src_graph[test_file]["compiled_in"]) == 3
    assert len(src_graph[test_file]["used_by"]) == 2

    src_info = c.load_src_info()
    assert src_info
    assert src_info[test_file]["loc"] == 11

    graph_part = c.load_src_graph([test_file])
    assert graph_part
    assert len(graph_part[test_file]["used_by"]) == 2
    assert len(src_graph[test_file]["compiled_in"]) == 3


def test_src_graph_empty_conf(tmpdir, cmds_file):
    c = SrcGraph(tmpdir)
    c.parse(cmds_file)

    src_graph = c.load_src_graph()
    assert src_graph
    assert len(src_graph[test_file]["used_by"]) >= 1
