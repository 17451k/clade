# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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
import shutil
import unittest.mock

from clade import Clade

test_file = os.path.abspath("tests/test_project/main.c")


def test_storage(tmpdir):
    c = Clade(tmpdir)

    c.add_file_to_storage(__file__)
    c.add_file_to_storage("do_not_exist.c")
    assert os.path.exists(os.path.join(c.storage_dir, __file__))
    assert c.get_storage_path(__file__)

    # Test possible race condition
    with unittest.mock.patch("shutil.copyfile") as copyfile_mock:
        copyfile_mock.side_effect = shutil.SameFileError
        c.add_file_to_storage(test_file)


def test_storage_with_conversion(tmpdir):
    c = Clade(tmpdir, conf={"Storage.convert_to_utf8": True})

    with unittest.mock.patch("os.replace") as replace_mock:
        replace_mock.side_effect = OSError
        c.add_file_to_storage(test_file)
