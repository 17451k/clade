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
import pytest
import shutil
import stat
import unittest.mock

from clade import Clade

test_file = os.path.abspath("tests/test_project/main.c")


def test_storage(tmpdir):
    c = Clade(tmpdir)

    returned_storage_path = c.add_file_to_storage(__file__)
    c.add_file_to_storage("do_not_exist.c")

    storage_path = c.get_storage_path(__file__)

    assert storage_path
    assert os.path.exists(storage_path)
    assert storage_path.startswith(c.storage_dir)
    assert returned_storage_path == storage_path

    # Test possible race condition
    with unittest.mock.patch("shutil.copyfile") as copyfile_mock:
        copyfile_mock.side_effect = shutil.SameFileError
        c.add_file_to_storage(test_file)


def test_storage_with_conversion(tmpdir):
    c = Clade(tmpdir, conf={"Storage.convert_to_utf8": True})

    with unittest.mock.patch("os.replace") as replace_mock:
        replace_mock.side_effect = OSError
        c.add_file_to_storage(test_file)


def test_files_to_add(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file, conf={"Storage.files_to_add": [__file__]})
    c.parse("Storage")

    storage_path = c.get_storage_path(__file__)
    assert storage_path
    assert os.path.exists(storage_path)


def test_folders_to_add(tmpdir, cmds_file):
    c = Clade(
        tmpdir, cmds_file, conf={"Storage.files_to_add": [os.path.dirname(__file__)]}
    )
    c.parse("Storage")

    storage_path = c.get_storage_path(__file__)
    assert storage_path
    assert os.path.exists(storage_path)


@pytest.mark.parametrize("encoding", ["cp1251", "utf8"])
def test_storage_encoding(tmpdir, encoding):
    c = Clade(tmpdir, conf={"Storage.convert_to_utf8": True})

    bstr = "мир".encode("cp1251")

    test_file = os.path.join(str(tmpdir), "test")
    with open(test_file, "wb") as fh:
        fh.write(bstr)

    c.add_file_to_storage(test_file, encoding=encoding)


@pytest.mark.parametrize("convert", [False, True])
def test_storage_permissions(tmpdir, convert):
    c = Clade(tmpdir, conf={"Storage.convert_to_utf8": convert})
    storage_path = c.add_file_to_storage(__file__)
    assert os.stat(storage_path)[stat.ST_MODE] == os.stat(__file__)[stat.ST_MODE]
