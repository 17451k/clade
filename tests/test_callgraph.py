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

from clade.extensions.callgraph import Callgraph

zero_c = "tests/test_project/zero.c"
main_c = "tests/test_project/main.c"


def callgraph_is_ok(c):
    callgraph = c.load_callgraph()

    call_line = "10"
    match_type = 4

    assert callgraph[zero_c]["zero"]["called_in"][main_c]["main"][call_line]["match_type"] == match_type
    assert callgraph[main_c]["main"]["calls"][zero_c]["zero"][call_line]["match_type"] == match_type


def callgraph_by_file_is_ok(c):
    callgraph = c.load_callgraph()
    callgraph_by_zero_c = c.load_callgraph([zero_c])

    for file in callgraph:
        if file == zero_c:
            assert callgraph_by_zero_c[zero_c] == callgraph[zero_c]
        else:
            assert file not in callgraph_by_zero_c


def calls_by_ptr_is_ok(c):
    calls_by_ptr = c.load_calls_by_ptr()
    assert calls_by_ptr[zero_c]["func_with_pointers"]["fp1"] == ["17"]
    assert calls_by_ptr[zero_c]["func_with_pointers"]["fp2"] == ["17"]


def used_in_is_ok(c):
    used_in = c.load_used_in()
    assert not used_in[zero_c]["zero"]["used_in_file"]
    assert used_in[zero_c]["zero"]["used_in_func"][zero_c]["func_with_pointers"]["15"] == 3
    assert used_in[zero_c]["zero"]["used_in_func"][zero_c]["func_with_pointers"]["16"] == 3


def test_callgraph(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = Callgraph(tmpdir, conf=conf)
    c.parse(cmds_file)

    callgraph_is_ok(c)
    callgraph_by_file_is_ok(c)
    calls_by_ptr_is_ok(c)
    used_in_is_ok(c)
