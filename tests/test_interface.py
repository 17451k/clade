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
from clade.cmds import iter_cmds, iter_cmds_by_which
from clade.envs import iter_envs

from tests.test_intercept import test_project_make, calculate_loc
from tests.test_functions import (
    funcs_are_ok,
    funcs_by_file_are_ok,
    funcs_are_consistent,
    filtered_funcs_by_file_are_ok,
)
from tests.test_callgraph import callgraph_is_ok, callgraph_by_file_is_ok
from tests.test_variables import variables_are_ok, used_in_vars_is_ok
from tests.test_typedefs import typedefs_are_ok
from tests.test_macros import definitions_are_ok, expansions_are_ok
from tests.test_cross_ref import (
    ref_to_are_ok,
    filtered_ref_to_are_ok,
    ref_from_are_ok,
    filtered_ref_from_are_ok,
)
from tests.test_project import main_c, zero_c


def test_intercept(tmpdir):
    output = os.path.join(str(tmpdir), "cmds.txt")

    c = Clade(cmds_file=output)

    assert not c.intercept(command=test_project_make, use_wrappers=True)
    assert os.path.isfile(output)
    assert calculate_loc(output) > 1


@pytest.mark.cif
def test_cmd_graph(clade_api: Clade):
    c = clade_api

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

        if c.get_cmd_type(cmd_id) in ["CC", "CXX"]:
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

    with pytest.raises(KeyError):
        assert c.get_cmd_type("-1")

    with pytest.raises(KeyError):
        assert c.get_root_cmds("-1")

    with pytest.raises(KeyError):
        assert c.get_leaf_cmds("-1")


@pytest.mark.cif
def test_src_graph(clade_api: Clade):
    c = clade_api

    assert c.src_graph
    for file in c.src_graph:
        assert c.get_compilation_cmds_by_file(file)
        assert c.get_file_size(file) > 0

    with pytest.raises(RuntimeError):
        assert c.get_file_size("this_file_does_not_exist.c")


@pytest.mark.cif
def test_pid_graph(clade_api: Clade):
    c = clade_api

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


@pytest.mark.cif
def test_callgraph(clade_api: Clade):
    c = clade_api

    callgraph = c.callgraph
    callgraph_by_zero_c = c.get_callgraph([zero_c], add_unknown=False)

    callgraph_is_ok(callgraph)
    callgraph_by_file_is_ok(callgraph, callgraph_by_zero_c)


@pytest.mark.cif
def test_functions(clade_api: Clade):
    c = clade_api

    funcs = c.functions
    funcs_by_file = c.functions_by_file
    funcs_by_main_c = c.get_functions_by_file([main_c], add_unknown=False)

    funcs_are_ok(funcs)
    funcs_by_file_are_ok(funcs_by_file)
    funcs_are_consistent(funcs, funcs_by_file)
    filtered_funcs_by_file_are_ok(funcs_by_file, funcs_by_main_c)


@pytest.mark.cif
def test_get_typedefs(clade_api: Clade):
    typedefs_are_ok(clade_api.get_typedefs())


@pytest.mark.cif
def test_get_variables(clade_api: Clade):
    variables_are_ok(clade_api.get_variables())


@pytest.mark.cif
def test_get_used_in_vars_functions(clade_api: Clade):
    used_in_vars_is_ok(clade_api.get_used_in_vars_functions())


@pytest.mark.cif
def test_get_macros_expansions(clade_api: Clade):
    c = clade_api

    assert c.get_macros_expansions(macros_names=["ZERO", "WEIRD_ZERO"])
    assert not c.get_macros_expansions(macros_names=["ZERO2"])

    expansions_are_ok(c.get_macros_expansions())


@pytest.mark.cif
def test_get_macros_definitions(clade_api: Clade):
    c = clade_api

    assert c.get_macros_definitions(macros_names=["ZERO", "WEIRD_ZERO"])
    assert not c.get_macros_definitions(macros_names=["ZERO2"])

    definitions_are_ok(c.get_macros_definitions())


@pytest.mark.cif
def test_cdb(clade_api: Clade):
    assert clade_api.compilation_database


@pytest.mark.cif
def test_meta_good(clade_api: Clade):
    c = clade_api

    assert c.get_conf()
    assert c.get_version()
    assert c.get_build_dir() == os.getcwd()

    test_data = {"test_data": 5}
    c.add_meta_by_key("test", test_data)
    assert test_data == c.get_meta_by_key("test")
    with pytest.raises(KeyError):
        assert c.get_meta_by_key("test2")

    assert c.get_uuid()


def test_get_meta_bad(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    with pytest.raises(RuntimeError):
        c.get_meta()


def test_add_meta_bad(tmpdir):
    c = Clade(tmpdir)

    with pytest.raises(RuntimeError):
        c.add_meta_by_key("test", None)


def test_check_work_dir_fail(tmpdir):
    c = Clade(tmpdir)

    assert not c.work_dir_ok()


def test_cant_create_work_dir():
    with pytest.raises(PermissionError):
        c = Clade("/clade_test")
        c.parse("CC")


@pytest.mark.cif
def test_check_work_dir(clade_api: Clade):
    assert clade_api.work_dir_ok(log=True)


def test_check_work_dir_bad(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)

    assert not c.work_dir_ok(log=True)


@pytest.mark.cif
def test_cross_ref(clade_api: Clade):
    c = clade_api

    ref_to = c.get_ref_to()

    ref_to_are_ok(ref_to)

    ref_to_main_c = c.get_ref_to([main_c])
    filtered_ref_to_are_ok(ref_to, ref_to_main_c)

    ref_from = c.get_ref_from()
    ref_from_are_ok(ref_from)

    ref_from_main_c = c.get_ref_from([main_c])
    filtered_ref_from_are_ok(ref_from, ref_from_main_c)


def test_parse_undef(tmpdir):
    with pytest.raises(NotImplementedError):
        c = Clade(tmpdir)
        c.parse("XYZ")


@pytest.mark.cif
def test_get_raw_cmds(clade_api: Clade):
    assert list(clade_api.get_raw_cmds()) == list(iter_cmds(clade_api.cmds_file))


@pytest.mark.cif
def test_get_raw_cmds_by_which(clade_api: Clade):
    assert list(clade_api.get_raw_cmds_by_which(["/usr/bin/make"])) == list(
        iter_cmds_by_which(clade_api.cmds_file, ["/usr/bin/make"])
    )


@pytest.mark.cif
def test_get_raw_cmd_by_id(clade_api: Clade):
    assert clade_api.get_raw_cmd_by_id(1)["id"] == 1


@pytest.mark.cif
def test_get_envs_by_id(clade_api: Clade):
    assert clade_api.get_envs_by_id(1) == list(clade_api.get_envs())[0]["envs"]


@pytest.mark.cif
def test_get_envs(clade_api: Clade):
    assert list(clade_api.get_envs()) == list(
        iter_envs(os.path.join(clade_api.work_dir, "envs.txt"))
    )


@pytest.mark.cif
def test_get_get_env_value_by_id(clade_api: Clade):
    assert (
        clade_api.get_env_value_by_id(1, "HOME")
        == list(iter_envs(os.path.join(clade_api.work_dir, "envs.txt")))[1]["envs"][
            "HOME"
        ]
    )
