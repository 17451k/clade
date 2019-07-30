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
from tests.test_project import main_c, zero_c, zero_h


def funcs_are_ok(funcs):
    assert not funcs["main"][main_c]["declarations"]
    assert funcs["main"][main_c]["line"] == "8"
    assert funcs["main"][main_c]["signature"] == "int main(void);"
    assert funcs["main"][main_c]["type"] == "global"
    assert len(funcs["print"]) >= 2


def funcs_by_file_are_ok(funcs_by_file):
    assert funcs_by_file
    assert set(funcs_by_file[zero_c]) == {"zero", "print", "func_with_pointers"}
    assert funcs_by_file[zero_c]["zero"]["declarations"][zero_h]["line"] == "1"
    # TODO: Fix aspectator to print proper signatures without errors in it
    # assert funcs_by_file[zero_c]["zero"]["declarations"][zero_h]["signature"] == "int zero(void);"
    assert funcs_by_file[zero_c]["zero"]["declarations"][zero_h]["type"] == "global"


def funcs_are_consistent(funcs, funcs_by_file):
    for func in funcs:
        for file in funcs[func]:
            assert funcs[func][file] == funcs_by_file[file][func]


def filtered_funcs_by_file_are_ok(funcs_by_file, funcs_by_main_c):
    for file in funcs_by_file:
        if file == main_c:
            assert funcs_by_main_c[main_c] == funcs_by_file[main_c]
        else:
            assert file not in funcs_by_main_c


def test_functions(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("Functions")

    funcs = e.load_functions()
    funcs_by_file = e.load_functions_by_file()
    funcs_by_main_c = e.load_functions_by_file([main_c])

    funcs_are_ok(funcs)
    funcs_by_file_are_ok(funcs_by_file)
    funcs_are_consistent(funcs, funcs_by_file)
    filtered_funcs_by_file_are_ok(funcs_by_file, funcs_by_main_c)
