# Copyright (c) 2021 ISP RAS (http://www.ispras.ru)
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


import pytest

from clade.envs import (
    open_envs_file,
    iter_envs,
    join_env,
    get_last_id,
    get_all_envs,
    get_stats,
)


def test_bad_open():
    with pytest.raises(RuntimeError):
        open_envs_file("do_not_exist.txt")


def test_iter(envs_file):
    assert len(list(iter_envs(envs_file))) > 0


def test_get_last_id(envs_file):
    assert int(get_last_id(envs_file)) > 0


def test_get_stats(envs_file):
    assert get_stats(envs_file)[1] > 0


def test_join_env(envs_file):
    lines = []
    for envs in iter_envs(envs_file):
        for name, value in envs["envs"].items():
            lines.append(join_env({name: value}))

    with open(envs_file, "r") as envs_fh:
        for line in envs_fh:
            line = line.strip()

            assert not line or line in lines


def test_get_all_envs(envs_file):
    envs = []
    for env in iter_envs(envs_file):
        envs.append(env)

    assert envs == get_all_envs(envs_file)
