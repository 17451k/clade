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

from clade.extensions.cc import CC
from clade.extensions.opts import preprocessor_deps_opts


def test_cc_load_deps_by_id(tmpdir, cmds_file):
    c = CC(tmpdir)
    c.parse(cmds_file)

    for cmd in c.load_all_cmds(compile_only=True):
        deps = c.load_deps_by_id(cmd["id"])
        assert deps

        for cmd_in in cmd["in"]:
            assert cmd_in in deps


@pytest.mark.parametrize("with_opts", [True, False])
@pytest.mark.parametrize("with_deps", [True, False])
def test_cc_load_all_cmds(tmpdir, cmds_file, with_opts, with_deps):
    conf = {"Common.with_opts": with_opts}

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    cmds = list(c.load_all_cmds(with_opts=with_opts, with_deps=with_deps))
    assert len(cmds) > 1

    for cmd in cmds:
        assert ("opts" in cmd) == with_opts
        assert ("deps" in cmd) == with_deps

        cmd_by_id = c.load_cmd_by_id(cmd["id"])

        assert cmd_by_id["id"] == cmd["id"]
        assert cmd_by_id["in"] == cmd["in"]
        assert cmd_by_id["out"] == cmd["out"]

        if with_opts:
            cmd["opts"] == c.load_opts_by_id(cmd["id"])

        if with_deps:
            cmd["deps"] == c.load_deps_by_id(cmd["id"])


@pytest.mark.parametrize("store_deps", [True, False])
def test_cc_store_deps(tmpdir, cmds_file, store_deps):
    conf = {"CC.store_deps": store_deps}

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    storage_dir = c.extensions["Storage"].get_storage_dir()

    for cmd in c.load_all_cmds(with_deps=True, compile_only=True):
        for file in cmd["deps"]:
            if not os.path.isabs(file):
                file = os.path.join(cmd["cwd"], file)

            assert os.path.exists(storage_dir + os.sep + file) == store_deps


@pytest.mark.parametrize("with_system_header_files", [True, False])
def test_cc_with_system_header_files(tmpdir, cmds_file, with_system_header_files):
    conf = {"CC.with_system_header_files": with_system_header_files}

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    for cmd in c.load_all_cmds(with_deps=True, compile_only=True):
        if not with_system_header_files:
            for file in cmd["deps"]:
                assert not re.match(r"/usr", file)
        else:
            for file in cmd["deps"]:
                if re.match(r"/usr", file):
                    break
            else:
                assert False


@pytest.mark.parametrize("ignore_cc1", [True, False])
def test_cc_ignore_cc1(tmpdir, cmds_file, ignore_cc1):
    conf = {"CC.ignore_cc1": ignore_cc1}

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    found_cc1 = False

    for cmd in c.load_all_cmds(with_opts=True):
        if"-cc1" in cmd["opts"]:
            found_cc1 = True

    assert ignore_cc1 != found_cc1


@pytest.mark.parametrize("save_unparsed_cmds", [True, False])
def test_cc_save_unparsed_cmds(tmpdir, cmds_file, save_unparsed_cmds):
    conf = {"Common.save_unparsed_cmds": save_unparsed_cmds}

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    for cmd in c.load_all_cmds():
        assert (c.load_unparsed_by_id(cmd["id"]) != dict()) == save_unparsed_cmds


@pytest.mark.parametrize("filter_deps", [True, False])
def test_cc_filter_deps(tmpdir, cmds_file, filter_deps):
    conf = {
        "CC.filter_deps": filter_deps
    }

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    found_deps_opt = False

    for cmd in c.load_all_cmds(with_opts=True):
        if set(preprocessor_deps_opts).intersection(cmd["opts"]):
            found_deps_opt = True

    assert filter_deps != found_deps_opt


@pytest.mark.parametrize("filter", [[], ["/dev/null"]])
@pytest.mark.parametrize("filter_in", [[], ["-"]])
@pytest.mark.parametrize("filter_out", [[], ["/dev/null"]])
def test_cc_filter(tmpdir, cmds_file, filter, filter_in, filter_out):
    conf = {
        "Common.filter": filter,
        "Common.filter_in": filter_in,
        "Common.filter_out": filter_out
    }

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    assert len(list(c.load_all_cmds()))


def test_cc_empty_conf(tmpdir, cmds_file):
    c = CC(tmpdir)
    c.parse(cmds_file)

    assert len(list(c.load_all_cmds()))


def test_cc_empty_which_list(tmpdir, cmds_file):
    conf = {
        "CC.which_list": []
    }

    c = CC(tmpdir, conf)
    c.parse(cmds_file)

    assert len(list(c.load_all_cmds())) == 0
