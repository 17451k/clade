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

from clade.cmds import iter_cmds, iter_cmds_by_which, open_cmds_file, get_build_cwd, get_last_id, get_stats, print_cmds_stats

# TODO: Replace >= by ==
number_of_cmds = 5
number_of_gcc_cmds = 2
gcc_which = shutil.which("gcc")


def test_bad_open(cmds_file):
    with pytest.raises(RuntimeError):
        open_cmds_file("do_not_exist.txt")


def test_iter(cmds_file):
    with open_cmds_file(cmds_file) as cmds_fp:
        assert len(list(iter_cmds(cmds_fp))) >= number_of_cmds


def test_iter_by_which(cmds_file):
    with open_cmds_file(cmds_file) as cmds_fp:
        assert len(list(iter_cmds_by_which(cmds_fp, [gcc_which]))) >= number_of_gcc_cmds


def test_get_build_cmd(cmds_file):
    assert get_build_cwd(cmds_file) == os.getcwd()


def test_get_last_id(cmds_file):
    assert int(get_last_id(cmds_file)) >= number_of_cmds


def test_get_stats(cmds_file):
    assert get_stats(cmds_file)[gcc_which] >= number_of_gcc_cmds


def test_print_stats(cmds_file):
    print_cmds_stats([cmds_file])


def test_print_stats_bad():
    with pytest.raises(SystemExit):
        print_cmds_stats([])
