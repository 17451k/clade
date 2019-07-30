# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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

from clade import Clade

zero_c = os.path.abspath("tests/test_project/zero.c")
zero_h = os.path.abspath("tests/test_project/zero.h")
main_c = os.path.abspath("tests/test_project/main.c")


def ref_to_are_ok(ref_to):
    assert ref_to[main_c]
    assert ref_to[zero_c]

    assert ref_to[main_c]["decl"]
    assert ref_to[main_c]["def"]

    assert ref_to[zero_c]["decl"]
    assert not ref_to[zero_c]["def"]

    assert [[10, 11, 15], [zero_h, 1]] in ref_to[main_c]["decl"]
    assert [[9, 4, 9], [main_c, 4]] in ref_to[main_c]["def"]
    assert [[10, 11, 15], [zero_c, 6]] in ref_to[main_c]["def"]


def filtered_ref_to_are_ok(rel_to, rel_to_main_c):
    for file in rel_to:
        if file == main_c:
            assert rel_to[main_c] == rel_to_main_c[main_c]
        else:
            assert file not in rel_to_main_c


def ref_from_are_ok(ref_from):
    assert ref_from[main_c]
    assert ref_from[zero_c]
    assert ref_from[zero_h]

    assert [[4, 12, 17], [main_c, [9]]] in ref_from[main_c]
    assert [[6, 4, 8], [main_c, [10]]] in ref_from[zero_c]
    assert [[1, 11, 15], [main_c, [10]]] in ref_from[zero_h]


def filtered_ref_from_are_ok(rel_from, rel_from_main_c):
    for file in rel_from:
        if file == main_c:
            assert rel_from[main_c] == rel_from_main_c[main_c]
        else:
            assert file not in rel_from_main_c


def test_functions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("CrossRef")

    ref_to = e.load_ref_to_by_file()
    ref_to_are_ok(ref_to)

    ref_to_main_c = e.load_ref_to_by_file([main_c])
    filtered_ref_to_are_ok(ref_to, ref_to_main_c)

    ref_from = e.load_ref_from_by_file()
    ref_from_are_ok(ref_from)

    ref_from_main_c = e.load_ref_from_by_file([main_c])
    filtered_ref_from_are_ok(ref_from, ref_from_main_c)
