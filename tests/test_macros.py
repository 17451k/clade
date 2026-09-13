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

from clade import Clade

zero_c = os.path.abspath("tests/test_project/zero.c")


def definitions_are_ok(definitions):
    assert definitions[zero_c]["WEIRD_ZERO"] == [3]
    assert definitions[zero_c]["ZERO"] == [4]


def expansions_are_ok(expansions):
    assert expansions[zero_c]["WEIRD_ZERO"]["args"] == [["10"]]
    assert expansions[zero_c]["ZERO"]


@pytest.mark.cif
def test_macros(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("Macros")

    definitions_are_ok(c.get_macros_definitions())
    expansions_are_ok(c.get_macros_expansions())

    from clade.extensions.macros import Expansion

    expansions = e.load_expansions()
    assert expansions[zero_c]["ZERO"][zero_c] == [{"exp_line": 7, "def_line": 4}]
    assert expansions[zero_c]["WEIRD_ZERO"][zero_c] == [{"exp_line": 7, "def_line": 3}]

    reversed_expansions = e.load_reversed_expansions()
    assert reversed_expansions[zero_c]["ZERO"][zero_c] == [
        {"exp_line": 7, "def_line": 4}
    ]
    assert reversed_expansions[zero_c]["WEIRD_ZERO"][zero_c] == [
        {"exp_line": 7, "def_line": 3}
    ]

    args = e.load_args()
    assert args[zero_c] == {"WEIRD_ZERO": [["10"]]}
    assert "ZERO" not in args[zero_c] or args[zero_c]["ZERO"] == []

    traversed = list(e.traverse_expansions())
    assert (
        Expansion(name="ZERO", def_file=zero_c, def_line=4, exp_file=zero_c, exp_line=7)
        in traversed
    )
    assert (
        Expansion(
            name="WEIRD_ZERO", def_file=zero_c, def_line=3, exp_file=zero_c, exp_line=7
        )
        in traversed
    )

    assert e.load_macros([zero_c])[zero_c] == [
        {"name": "WEIRD_ZERO", "line": 3},
        {"name": "ZERO", "line": 4},
    ]
