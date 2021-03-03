# Copyright (c) 2020 ISP RAS (http://www.ispras.ru)
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
from clade.scripts.tracer import Tracer


@pytest.mark.cif
def test_tracer(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file, preset="klever_linux_kernel")
    c.parse_list(c.conf["extensions"])

    print(c.work_dir)
    t = Tracer(c.work_dir)

    from_func = t.find_functions(["main"])[0]
    to_func = t.find_functions(["printf"])[0]
    trace = t.trace(from_func, to_func)
    assert len(trace) == 2
