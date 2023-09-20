# Copyright (c) 2022 Ilya Shchepetkov
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


def used_in_is_ok(used_in):
    assert not used_in[zero_c]["zero"]["used_in_file"]
    assert {"line": 15, "match": 3} in used_in[zero_c]["zero"]["used_in_func"][zero_c][
        "func_with_pointers"
    ]
    assert {"line": 16, "match": 3} in used_in[zero_c]["zero"]["used_in_func"][zero_c][
        "func_with_pointers"
    ]


@pytest.mark.cif
def test_used_in(tmpdir, cmds_file):
    conf = {"CmdGraph.requires": ["CC", "MV"]}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("UsedIn")

    used_in = e.load_used_in()

    used_in_is_ok(used_in)
