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
from clade.extensions.opts import filter_opts, filter_opts_for_clang


def test_isysroot(tmpdir):
    c = Clade(tmpdir)

    opts = ["-isysroot=/test/path", "-I/usr/include"]

    filtered_opts = filter_opts(opts, c.get_storage_path)

    assert len(filtered_opts) == len(opts)
    assert filtered_opts[0] == f"-isysroot={c.storage_dir}/test/path"
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


def test_separate_value(tmpdir):
    c = Clade(tmpdir)

    opts = ["-I", "/usr/include", "-D", "X=1"]

    filtered_opts = filter_opts(opts, c.get_storage_path)

    assert filtered_opts == ["-I", f"{c.storage_dir}/usr/include", "-D", "X=1"]


def test_isysroot_separate(tmpdir):
    c = Clade(tmpdir)

    opts = ["-isysroot", "/sdk", "-I", "/usr/include"]

    filtered_opts = filter_opts(opts, c.get_storage_path)

    # isysroot's value is routed through storage
    assert filtered_opts[0] == "-isysroot"
    assert filtered_opts[1] == f"{c.storage_dir}/sdk"

    # since isysroot is present, the -I value is left unchanged
    assert filtered_opts[2] == "-I"
    assert filtered_opts[3] == "/usr/include"


def test_relative_include_unchanged(tmpdir):
    c = Clade(tmpdir)

    opts = ["-Iinclude"]

    assert filter_opts(opts, c.get_storage_path) == ["-Iinclude"]


def test_clang_opts():
    opts = ["--target=x86_64", "-O2", "-Wall"]

    assert filter_opts_for_clang(opts) == ["--target=x86_64", "-O2"]

    # --target is only supported for clang, not for the default (gcc) regex
    assert filter_opts(["--target=x86_64"]) == []


def test_optimization_exact_match():
    # gcc_optimization_opts are matched with a "$" anchor, so "-O3x" is not
    # a valid optimization option and must not be included
    opts = ["-O3", "-Os", "-Ofast", "-O3x"]

    assert filter_opts(opts) == ["-O3", "-Os", "-Ofast"]
