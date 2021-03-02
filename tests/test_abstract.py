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

import pytest
import os
import unittest.mock

from clade import Clade


def test_cc_parallel(tmpdir, cmds_file):
    del os.environ["CLADE_DEBUG"]

    try:
        c = Clade(tmpdir, cmds_file)
        e = c.parse("CC")

        assert e.load_all_cmds()
    finally:
        os.environ["CLADE_DEBUG"] = "1"


def test_cc_parallel_with_exception(tmpdir, cmds_file):
    del os.environ["CLADE_DEBUG"]

    try:
        # Force results() method of a future object to raise Exception
        with unittest.mock.patch("concurrent.futures.Future.result") as result_mock:
            result_mock.side_effect = Exception

            c = Clade(tmpdir, cmds_file)
            with pytest.raises(Exception):
                c.parse("CC")
    finally:
        os.environ["CLADE_DEBUG"] = "1"


def test_cc_parallel_with_print(tmpdir, cmds_file):
    del os.environ["CLADE_DEBUG"]

    try:
        with unittest.mock.patch("sys.stdout.isatty") as isatty_mock:
            isatty_mock.return_value = True

            c = Clade(tmpdir, cmds_file)
            e = c.parse("CC")

            assert e.load_all_cmds()
    finally:
        os.environ["CLADE_DEBUG"] = "1"


@pytest.mark.parametrize("force", [True, False])
def test_force(tmpdir, cmds_file, force):
    conf = {"force": force}

    c1 = Clade(tmpdir, cmds_file, conf=conf)
    c1.parse("CC")

    p_work_dir = os.path.join(str(tmpdir), "PidGraph")
    c_work_dir = os.path.join(str(tmpdir), "CC")

    p_mtime1 = os.stat(p_work_dir).st_mtime
    c_mtime1 = os.stat(c_work_dir).st_mtime

    c2 = Clade(tmpdir, cmds_file, conf=conf)
    c2.parse("CC")

    p_mtime2 = os.stat(p_work_dir).st_mtime
    c_mtime2 = os.stat(c_work_dir).st_mtime

    assert force != (p_mtime1 == p_mtime2)
    assert force != (c_mtime1 == c_mtime2)


@pytest.mark.parametrize("clean", [True, False])
def test_parse_clean(tmpdir, cmds_file, clean):
    c = Clade(tmpdir, cmds_file)
    c.parse("CC", clean=clean)

    p_work_dir = os.path.join(str(tmpdir), "PidGraph")
    c_work_dir = os.path.join(str(tmpdir), "CC")

    p_mtime1 = os.stat(p_work_dir).st_mtime
    c_mtime1 = os.stat(c_work_dir).st_mtime

    c.parse("CC", clean=clean)

    p_mtime2 = os.stat(p_work_dir).st_mtime
    c_mtime2 = os.stat(c_work_dir).st_mtime

    assert clean != (c_mtime1 == c_mtime2)
    assert p_mtime1 == p_mtime2


def test_check_conf_consistency(tmpdir, cmds_file):
    conf = {"PidGraph.filter_cmds_by_pid": True}

    c = Clade(tmpdir, cmds_file, conf=conf)
    c.parse("PidGraph")

    changed_conf = {"PidGraph.filter_cmds_by_pid": False}

    c = Clade(tmpdir, cmds_file, conf=changed_conf)
    with pytest.raises(RuntimeError):
        c.parse("CC")
