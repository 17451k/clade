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

from clade.intercept import Interceptor
from tests.test_intercept import test_project_make


@pytest.fixture(scope="session")
def cmds_file():
    test_cmds_file = os.path.join(os.path.dirname(__file__), "test_project", "cmds.txt")

    if not os.path.isfile(test_cmds_file):
        i = Interceptor(command=test_project_make, output=test_cmds_file, fallback=True)
        i.execute()

    yield test_cmds_file

    os.remove(test_cmds_file)
