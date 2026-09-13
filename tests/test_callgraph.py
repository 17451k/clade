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

import pytest

from clade import Clade
from tests.test_project import main_c, zero_c


def callgraph_is_ok(callgraph):
    call_line = 10
    match_type = 4

    assert {"match": match_type, "line": call_line} in callgraph[zero_c]["zero"][
        "called_in"
    ][main_c]["main"]
    assert {"match": match_type, "line": call_line} in callgraph[main_c]["main"][
        "calls"
    ][zero_c]["zero"]

    assert callgraph[main_c]["main"]["calls"][main_c]["print"] == [
        {"line": 9, "match": 5}
    ]
    assert "print" not in callgraph[main_c]["main"]["calls"].get(zero_c, {})
    assert callgraph[main_c]["main"]["calls"][zero_c]["zero"] == [
        {"line": 10, "match": 4}
    ]
    assert callgraph["unknown"]["printf"]["called_in"][main_c]["print"] == [
        {"line": 5, "match": 1}
    ]
    assert callgraph["unknown"]["printf"]["called_in"][zero_c]["print"] == [
        {"line": 11, "match": 1}
    ]
    assert callgraph[main_c]["print"]["type"] == "static"
    assert callgraph[zero_c]["zero"]["type"] == "extern"
    assert "called_in" not in callgraph[zero_c]["print"]


def callgraph_by_file_is_ok(callgraph, callgraph_by_zero_c):
    for file in callgraph:
        if file == zero_c:
            assert callgraph_by_zero_c[zero_c] == callgraph[zero_c]
        else:
            assert file not in callgraph_by_zero_c


@pytest.mark.cif
def test_callgraph(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("Callgraph")

    callgraph = e.load_callgraph()
    callgraph_by_zero_c = e.load_callgraph([zero_c])

    callgraph_is_ok(callgraph)
    callgraph_by_file_is_ok(callgraph, callgraph_by_zero_c)

    calls = {
        (x.from_func, x.to_func, x.val["match"])
        for x in e.traverse_calls()
        if x.from_file in (main_c, zero_c)
    }
    assert calls == {("print", "printf", 1), ("main", "print", 5), ("main", "zero", 4)}

    called_in = {
        (x.from_func, x.to_func, x.val["match"])
        for x in e.traverse_called_in()
        if x.from_file in (main_c, zero_c)
    }
    assert called_in == calls

    unknown_callgraph = e.load_callgraph(["unknown"])
    assert "unknown" in unknown_callgraph
    assert main_c not in unknown_callgraph
