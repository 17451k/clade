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

from clade import Clade
from clade.extensions.opts import filter_opts


def test_isysroot(tmpdir):
    c = Clade(tmpdir)

    opts = ["-isysroot=/test/path", "-I/usr/include"]

    filtered_opts = filter_opts(opts, c.get_storage_path)

    assert len(filtered_opts) == len(opts)
    assert filtered_opts[0] == "-isysroot={}/test/path".format(c.storage_dir)
    assert filtered_opts[1] == opts[1]


def test_no_isysroot(tmpdir):
    c = Clade(tmpdir)

    opts = ["-I/usr/include"]

    filtered_opts = filter_opts(opts, c.get_storage_path)

    assert len(filtered_opts) == len(opts)
    assert filtered_opts[0] == f"-I{c.storage_dir}/usr/include"


def test_no_get_storage_path():
    opts = ["-I/usr/include"]

    assert filter_opts(opts) == opts


def test_bad_opt():
    opts = ["-ABC", "-Dtest"]

    assert filter_opts(opts) == ["-Dtest"]
