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

from clade import Clade
from tests.test_intercept import test_project_make, calculate_loc

main_c = "tests/test_project/main.c"


def test_intercept(tmpdir):
    output = os.path.join(str(tmpdir), "cmds.txt")

    c = Clade(cmds_file=output)

    assert not c.intercept(command=test_project_make, fallback=True)
    assert os.path.isfile(output)
    assert calculate_loc(output) > 1


def test_cmd_graph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    assert c.cmd_graph

    comp_cmds = c.compilation_cmds
    cc_cmds = c.get_all_cmds_by_type("CC")
    assert comp_cmds
    assert cc_cmds

    for cmd in comp_cmds:
        assert cmd["id"] in (x["id"] for x in cc_cmds)

    cmd_ids = c.cmd_ids
    assert cmd_ids
    assert len(cmd_ids) == len(c.cmds)

    for cmd_id in c.cmd_ids:
        assert c.get_cmd(cmd_id)

        for with_opts in (True, False):
            assert ("opts" in c.get_cmd(cmd_id, with_opts=with_opts)) == with_opts

        if c.get_cmd_type(cmd_id) == "CC":
            for with_deps in (True, False):
                assert ("deps" in c.get_cmd(cmd_id, with_deps=with_deps)) == with_deps
        else:
            with pytest.raises(RuntimeError):
                c.get_cmd(cmd_id, with_deps=True)

            with pytest.raises(RuntimeError):
                c.get_cc_deps(cmd_id)

    for cmd_id in c.cmd_ids:
        root_cmds = c.get_root_cmds(cmd_id)

        for cmd in c.get_root_cmds_by_type(cmd_id, "CC"):
            assert cmd in root_cmds

        assert len(root_cmds) >= len(c.cmd_graph[cmd_id]["using"])
        assert len(c.get_leaf_cmds(cmd_id)) >= len(c.cmd_graph[cmd_id]["used_by"])

    with pytest.raises(RuntimeError):
        assert c.get_cmd_type("-1")

    with pytest.raises(RuntimeError):
        assert c.get_root_cmds("-1")

    with pytest.raises(RuntimeError):
        assert c.get_leaf_cmds("-1")


def test_src_graph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.src_graph
    for file in c.src_graph:
        assert c.get_compilation_cmds_by_file(file)
        assert c.get_file_size(file) > 0

    with pytest.raises(RuntimeError):
        assert c.get_file_size("this_file_does_not_exist.c")

def test_pid_graph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.pid_graph
    assert c.pid_by_id

    for cmd_id in c.cmd_ids:
        assert cmd_id in c.pid_graph
        assert cmd_id in c.pid_by_id


def test_storage(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    c.add_file_to_storage(__file__)
    assert os.path.exists(os.path.join(c.storage_dir, __file__))


def test_callgraph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert len(c.callgraph.keys()) > 1
    assert len(c.get_callgraph([main_c]).keys()) > 1


def test_functions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.functions
    assert c.functions_by_file
    assert len(c.get_functions_by_file([main_c]).keys()) > 1


def test_get_typedefs(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_typedefs()


def test_get_variables(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_variables()


def test_get_used_in_vars_functions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_used_in_vars_functions()


def test_get_macros_expansions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_macros_expansions(macros_names=["ZERO", "WEIRD_ZERO"])
    assert not c.get_macros_expansions(macros_names=["ZERO2"])
    assert c.get_macros_expansions()


def test_get_macros_definitions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_macros_definitions(macros_names=["ZERO", "WEIRD_ZERO"])
    assert not c.get_macros_definitions(macros_names=["ZERO2"])
    assert c.get_macros_definitions()


def test_cdb(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.compilation_database
