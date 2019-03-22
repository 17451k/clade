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

from clade.extensions.functions import Functions

zero_c = os.path.abspath("tests/test_project/zero.c")
zero_h = os.path.abspath("tests/test_project/zero.h")
main_c = os.path.abspath("tests/test_project/main.c")


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

    c = Functions(tmpdir, conf)
    c.parse(cmds_file)

    funcs = c.load_functions()
    funcs_by_file = c.load_functions_by_file()
    funcs_by_main_c = c.load_functions_by_file([main_c])

    funcs_are_ok(funcs)
    funcs_by_file_are_ok(funcs_by_file)
    funcs_are_consistent(funcs, funcs_by_file)
    filtered_funcs_by_file_are_ok(funcs_by_file, funcs_by_main_c)
