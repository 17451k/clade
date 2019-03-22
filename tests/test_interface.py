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
from tests.test_functions import funcs_are_ok, funcs_by_file_are_ok, funcs_are_consistent, filtered_funcs_by_file_are_ok
from tests.test_callgraph import callgraph_is_ok, callgraph_by_file_is_ok
from tests.test_variables import variables_are_ok, used_in_vars_is_ok
from tests.test_typedefs import typedefs_are_ok
from tests.test_macros import definitions_are_ok, expansions_are_ok

main_c = os.path.abspath("tests/test_project/main.c")
zero_c = os.path.abspath("tests/test_project/zero.c")


def test_intercept(tmpdir):
    output = os.path.join(str(tmpdir), "cmds.txt")

    c = Clade(cmds_file=output)

    assert not c.intercept(command=test_project_make, use_wrappers=True)
    assert os.path.isfile(output)
    assert calculate_loc(output) > 1


def test_cmd_graph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    assert c.cmd_graph

    comp_cmds = c.compilation_cmds
    cc_cmds = c.get_all_cmds_by_type("CC")
    assert comp_cmds
    assert cc_cmds
    assert comp_cmds == c.get_compilation_cmds()

    for cmd in c.get_compilation_cmds(with_opts=True, with_raw=True, with_deps=True):
        assert cmd["id"] in (x["id"] for x in cc_cmds)
        assert "opts" in cmd
        assert "command" in cmd
        assert "deps" in cmd

    cmd_ids = c.cmd_ids
    assert cmd_ids
    assert len(cmd_ids) == len(c.cmds)
    assert c.cmds == c.get_cmds()

    for cmd_id in c.cmd_ids:
        assert c.get_cmd(cmd_id)

        for with_opts in (True, False):
            assert ("opts" in c.get_cmd(cmd_id, with_opts=with_opts)) == with_opts

        assert "command" in c.get_cmd(cmd_id, with_raw=True)

        if c.get_cmd_type(cmd_id) == "CC":
            for with_deps in (True, False):
                assert ("deps" in c.get_cmd(cmd_id, with_deps=with_deps)) == with_deps
        else:
            with pytest.raises(RuntimeError):
                c.get_cmd(cmd_id, with_deps=True)

            with pytest.raises(RuntimeError):
                c.get_cmd_deps(cmd_id)

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
    assert c.get_storage_path(__file__)


def test_callgraph(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    callgraph = c.callgraph
    callgraph_by_zero_c = c.get_callgraph([zero_c], add_unknown=False)

    callgraph_is_ok(callgraph)
    callgraph_by_file_is_ok(callgraph, callgraph_by_zero_c)


def test_functions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    funcs = c.functions
    funcs_by_file = c.functions_by_file
    funcs_by_main_c = c.get_functions_by_file([main_c], add_unknown=False)

    funcs_are_ok(funcs)
    funcs_by_file_are_ok(funcs_by_file)
    funcs_are_consistent(funcs, funcs_by_file)
    filtered_funcs_by_file_are_ok(funcs_by_file, funcs_by_main_c)


def test_get_typedefs(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    typedefs_are_ok(c.get_typedefs())


def test_get_variables(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    variables_are_ok(c.get_variables())


def test_get_used_in_vars_functions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    used_in_vars_is_ok(c.get_used_in_vars_functions())


def test_get_macros_expansions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_macros_expansions(macros_names=["ZERO", "WEIRD_ZERO"])
    assert not c.get_macros_expansions(macros_names=["ZERO2"])

    expansions_are_ok(c.get_macros_expansions())


def test_get_macros_definitions(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_macros_definitions(macros_names=["ZERO", "WEIRD_ZERO"])
    assert not c.get_macros_definitions(macros_names=["ZERO2"])

    definitions_are_ok(c.get_macros_definitions())

def test_cdb(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.compilation_database


def test_meta(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert c.get_conf()
    assert c.get_version()
    assert c.get_build_dir() == os.getcwd()

    test_data = {"test_data": 5}
    c.add_meta_by_key("test", test_data)
    assert test_data == c.get_meta_by_key("test")
    with pytest.raises(KeyError):
        assert c.get_meta_by_key("test2")

    assert c.get_uuid()


def test_parse_all(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    c.parse_all()
