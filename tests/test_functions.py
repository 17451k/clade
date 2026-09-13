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
from tests.test_project import main_c, zero_c, zero_h


def funcs_are_ok(funcs):
    assert len(funcs["main"]) == 1
    definition = funcs["main"][0]

    assert not definition["declarations"]
    assert definition["line"] == 8
    assert definition["signature"] == "int main(void);"
    assert definition["type"] == "extern"
    assert len(funcs["print"]) >= 2

    prints = funcs["print"]
    assert len(prints) == 2
    assert all(d["type"] == "static" for d in prints)
    assert {d["file"] for d in prints} == {main_c, zero_c}
    assert {d["line"] for d in prints} == {4, 10}
    assert all(d["declarations"] == [] for d in prints)

    zero_decls = funcs["zero"][0]["declarations"]
    assert len(zero_decls) == 1
    assert zero_decls[0]["file"] == zero_h
    assert zero_decls[0]["line"] == 1
    assert zero_decls[0]["signature"] == "int zero();"
    assert zero_decls[0]["type"] == "extern"

    printfs = funcs["printf"]
    assert len(printfs) == 1
    printf_def = printfs[0]
    assert printf_def["file"] == "unknown"
    assert printf_def["line"] is None
    assert printf_def["signature"] is None
    assert printf_def["compiled_in"] == [0]
    assert printf_def["declarations"]
    assert any(
        d["file"].endswith("stdio.h") or d["file"].endswith("_printf.h")
        for d in printf_def["declarations"]
    )
    assert printf_def["declarations"][0]["signature"].startswith("int printf(")

    assert funcs["func_with_pointers"][0]["line"] == 14

    main_def = funcs["main"][0]
    zero_def = funcs["zero"][0]
    assert set(main_def["compiled_in"]) == set(zero_def["compiled_in"])
    assert len(main_def["compiled_in"]) >= 1


def funcs_by_file_are_ok(funcs_by_file):
    assert funcs_by_file
    assert sorted([d["name"] for d in funcs_by_file[zero_c]]) == sorted(
        [
            "zero",
            "print",
            "func_with_pointers",
        ]
    )

    for definition in funcs_by_file[zero_c]:
        if definition["name"] != "zero":
            continue
        for declaration in definition["declarations"]:
            if declaration["file"] != zero_h:
                continue
            assert declaration["line"] == 1
            assert declaration["signature"] == "int zero();"
            assert declaration["type"] == "extern"


def funcs_are_consistent(funcs, funcs_by_file):
    for func in funcs:
        for definition in funcs[func]:
            definition = dict(definition)
            file = definition["file"]
            definition["name"] = func
            del definition["file"]
            assert definition in funcs_by_file[file]

    for file in funcs_by_file:
        for definition in funcs_by_file[file]:
            definition = dict(definition)
            func = definition["name"]
            definition["file"] = file
            del definition["name"]
            assert definition in funcs[func]


def filtered_funcs_by_file_are_ok(funcs_by_file, funcs_by_main_c):
    for file in funcs_by_file:
        if file == main_c:
            assert funcs_by_main_c[main_c] == funcs_by_file[main_c]
        else:
            assert file not in funcs_by_main_c


@pytest.mark.cif
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

    assert len(e.load_definitions("print")) == 2
    assert e.load_definitions("nope") == []
    assert e.function_exists("main")
    assert not e.function_exists("nope")
    assert e.definitions_exist(main_c)

    stripped = list(e.yield_functions_by_file([main_c], strip_list=["compiled_in"]))
    assert len(stripped) == 1
    for file, funcs_data in stripped:
        for definition in funcs_data[file]:
            assert "compiled_in" not in definition
            for declaration in definition.get("declarations", []):
                assert "compiled_in" not in declaration
