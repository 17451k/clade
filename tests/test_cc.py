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
import re

from clade import Clade
from clade.extensions.opts import cc_preprocessor_opts


def test_cc_load_deps_by_id(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("CC")

    for cmd in e.load_all_cmds(compile_only=True):
        deps = e.load_deps_by_id(cmd["id"])
        assert deps

        for cmd_in in cmd["in"]:
            assert cmd_in in deps


@pytest.mark.parametrize("with_opts", [True, False])
@pytest.mark.parametrize("with_deps", [True, False])
def test_cc_load_all_cmds(tmpdir, cmds_file, with_opts, with_deps):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("CC")

    cmds = list(e.load_all_cmds(with_opts=with_opts, with_deps=with_deps))
    assert len(cmds) > 1

    for cmd in cmds:
        assert ("opts" in cmd) == with_opts
        assert ("deps" in cmd) == with_deps

        cmd_by_id = e.load_cmd_by_id(cmd["id"])

        assert cmd_by_id["id"] == cmd["id"]
        assert cmd_by_id["in"] == cmd["in"]
        assert cmd_by_id["out"] == cmd["out"]

        if with_opts:
            assert cmd["opts"] == e.load_opts_by_id(cmd["id"])

        if with_deps:
            assert cmd["deps"] == e.load_deps_by_id(cmd["id"])


@pytest.mark.parametrize("store_deps", [True, False])
def test_cc_store_deps(tmpdir, cmds_file, store_deps):
    conf = {"Compiler.store_deps": store_deps}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    storage_dir = e.extensions["Storage"].get_storage_dir()

    for cmd in e.load_all_cmds(with_deps=True, compile_only=True):
        for file in cmd["deps"]:
            if not os.path.isabs(file):
                file = os.path.join(cmd["cwd"], file)

            assert os.path.exists(storage_dir + os.sep + file) == store_deps


@pytest.mark.parametrize("with_system_header_files", [True, False])
def test_cc_with_system_header_files(tmpdir, cmds_file, with_system_header_files):
    conf = {"CC.with_system_header_files": with_system_header_files}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    for cmd in e.load_all_cmds(with_deps=True, compile_only=True):
        if not with_system_header_files:
            for file in cmd["deps"]:
                assert not re.search(r"/usr", file)
        else:
            for file in cmd["deps"]:
                if re.search(r"/usr", file):
                    break
            else:
                assert False


@pytest.mark.parametrize("ignore_cc1", [True, False])
def test_cc_ignore_cc1(tmpdir, cmds_file, ignore_cc1):
    conf = {"CC.ignore_cc1": ignore_cc1}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    found_cc1 = False

    for cmd in e.load_all_cmds(with_opts=True):
        if "-cc1" in cmd["opts"]:
            found_cc1 = True

    if ignore_cc1 or found_cc1:
        assert ignore_cc1 != found_cc1


@pytest.mark.parametrize("compile_only", [True, False])
def test_cc_exclude_list_deps(tmpdir, cmds_file, compile_only):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("CC")

    found_deps_opt = False

    for cmd in e.load_all_cmds(with_opts=True, compile_only=compile_only):
        if set(cc_preprocessor_opts).intersection(cmd["opts"]):
            found_deps_opt = True

    assert compile_only != found_deps_opt


@pytest.mark.parametrize("exclude_list", [[], ["/dev/null"]])
@pytest.mark.parametrize("exclude_list_in", [[], ["-"]])
@pytest.mark.parametrize("exclude_list_out", [[], ["/dev/null"]])
def test_cc_exclude_list(
    tmpdir, cmds_file, exclude_list, exclude_list_in, exclude_list_out
):
    conf = {
        "Common.exclude_list": exclude_list,
        "Common.exclude_list_in": exclude_list_in,
        "Common.exclude_list_out": exclude_list_out,
    }

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    assert len(list(e.load_all_cmds()))


@pytest.mark.parametrize("include_list", [[], ["test_project"]])
def test_cc_include_list(tmpdir, cmds_file, include_list):
    conf = {"Common.include_list": include_list}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    assert len(list(e.load_all_cmds()))


def test_cc_empty_conf(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    e = c.parse("CC")

    assert len(list(e.load_all_cmds()))


def test_cc_empty_which_list(tmpdir, cmds_file):
    conf = {"CC.which_list": []}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    assert len(list(e.load_all_cmds())) == 0


def test_cc_preprocess(tmpdir, cmds_file):
    conf = {"Compiler.preprocess_cmds": True}

    c = Clade(tmpdir, cmds_file, conf)
    e = c.parse("CC")

    assert e.get_all_pre_files()
