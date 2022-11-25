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
from tests.test_project import zero_c


def variables_are_ok(variables):
    assert variables[zero_c]
    assert variables[zero_c][0]["declaration"] == "int (*fp3[1U])(void)"
    assert variables[zero_c][0]["path"] == zero_c
    assert variables[zero_c][0]["type"] == "extern"
    assert variables[zero_c][0]["value"][0]["index"] == 0
    assert variables[zero_c][0]["value"][0]["value"] == " & zero"
    assert variables[zero_c][1]["type"] == "static"


def used_in_vars_is_ok(used_in_vars):
    assert used_in_vars["zero"][zero_c] == [zero_c]


@pytest.mark.cif
def test_variables(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("Variables")

    variables_are_ok(e.load_variables())
    used_in_vars_is_ok(e.load_used_in_vars())
