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

from clade.extensions.macros import Macros

zero_c = "tests/test_project/zero.c"


def test_macros(tmpdir, cmds_file):
    c = Macros(tmpdir)
    c.parse(cmds_file)

    definitions = c.load_macros_definitions()
    assert definitions[zero_c]["WEIRD_ZERO"] == ["3"]
    assert definitions[zero_c]["ZERO"] == ["4"]

    expansions = c.load_macros_expansions()
    assert expansions[zero_c]["WEIRD_ZERO"]
    # TODO: Fix in CIF
    # assert expansions[zero_c]["ZERO"]
