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
    c.parse("Macros")

    definitions_are_ok(c.get_macros_definitions())
    expansions_are_ok(c.get_macros_expansions())
