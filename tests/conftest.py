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
import shutil
import tempfile

from clade import Clade
from clade.intercept import intercept
from tests.test_intercept import test_project_make, test_project


@pytest.fixture(scope="session")
def cmds_file():
    # Disable multiprocessing
    os.environ["CLADE_DEBUG"] = "1"

    with tempfile.NamedTemporaryFile() as fh:
        intercept(command=test_project_make, output=fh.name, use_wrappers=True)
        yield fh.name


@pytest.fixture(scope="session")
def envs_file():
    # Disable multiprocessing
    os.environ["CLADE_DEBUG"] = "1"

    c = Clade(work_dir=test_project + "/clade")
    c.intercept(command=test_project_make, use_wrappers=True, intercept_envs=True)
    yield os.path.join(c.work_dir, "envs.txt")


@pytest.fixture(scope="session")
def clade_api(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("Clade")

    c = Clade(tmpdir)
    c.intercept(command=test_project_make, use_wrappers=True, intercept_envs=True)
    c.parse_list(["CrossRef", "Variables", "Macros", "Typedefs", "CDB"])

    yield c


def pytest_collection_modifyitems(config, items):
    skip_cif = pytest.mark.skipif(
        not shutil.which("cif"), reason="cif is not installed"
    )

    for item in items:
        if "cif" in item.keywords:
            item.add_marker(skip_cif)
