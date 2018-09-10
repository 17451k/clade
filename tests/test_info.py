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

from clade.extensions.info import Info


def test_info(tmpdir, cmds_file):
    conf = {"CC.filter_deps": False, "Info.extra CIF opts": ["-hello"]}

    c = Info(tmpdir, conf)
    c.parse(cmds_file)

    assert list(c.iter_definitions())
    assert list(c.iter_declarations())
    assert not list(c.iter_exported())
    assert list(c.iter_calls())
    assert list(c.iter_calls_by_pointers())
    assert list(c.iter_functions_usages())
    assert list(c.iter_macros_definitions())
    assert list(c.iter_macros_expansions())
    assert list(c.iter_typedefs())
