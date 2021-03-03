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


@pytest.mark.cif
def test_info(tmpdir, cmds_file):
    conf = {"CC.filter_deps": False, "Info.extra_CIF_pts": ["-hello"]}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("Info")

    assert list(e.iter_definitions())
    assert list(e.iter_declarations())
    assert not list(e.iter_exported())
    assert list(e.iter_calls())
    assert list(e.iter_calls_by_pointers())
    assert list(e.iter_functions_usages())
    assert list(e.iter_macros_definitions())
    assert list(e.iter_macros_expansions())
    assert list(e.iter_typedefs())
