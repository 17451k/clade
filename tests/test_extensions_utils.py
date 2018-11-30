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

from clade.extensions.cc import CC
from clade.extensions.utils import common_main


def test_common_main(tmpdir, cmds_file):
    common_main(CC, ["-w", str(tmpdir), cmds_file])


def test_common_main_bad_conf(tmpdir, cmds_file):
    with pytest.raises(SystemExit):
        common_main(CC, ["-w", str(tmpdir), "-c", "does_not_exist.conf", cmds_file])


def test_common_main_bad_preset(tmpdir, cmds_file):
    with pytest.raises(SystemExit):
        common_main(CC, ["-w", str(tmpdir), "-p", "does_not_exist", cmds_file])
