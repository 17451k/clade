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

import os
import unittest.mock

import pytest

from clade import Clade
from clade.extensions.cc import CC
from clade.extensions.pid_graph import PidGraph


def parse_spy(cls):
    """Wrap cls.parse so that a test can see whether it ran."""
    return unittest.mock.patch.object(
        cls, "parse", autospec=True, side_effect=cls.parse
    )


def test_cc_parallel(tmpdir, cmds_file, monkeypatch):
    monkeypatch.delenv("CLADE_DEBUG")

    c = Clade(tmpdir, cmds_file)
    e = c.parse("CC")

    assert e.load_all_cmds()


def test_cc_parallel_with_exception(tmpdir, cmds_file, monkeypatch):
    monkeypatch.delenv("CLADE_DEBUG")

    # Force results() method of a future object to raise an exception
    with unittest.mock.patch("concurrent.futures.Future.result") as result_mock:
        result_mock.side_effect = RuntimeError("mocked future failure")

        c = Clade(tmpdir, cmds_file)
        with pytest.raises(RuntimeError, match="mocked future failure"):
            c.parse("CC")


def test_cc_parallel_with_print(tmpdir, cmds_file, monkeypatch):
    monkeypatch.delenv("CLADE_DEBUG")

    with unittest.mock.patch("sys.stdout.isatty") as isatty_mock:
        isatty_mock.return_value = True

        c = Clade(tmpdir, cmds_file)
        e = c.parse("CC")

        assert e.load_all_cmds()


@pytest.mark.parametrize("force", [True, False])
def test_force(tmpdir, cmds_file, force):
    conf = {"force": force}

    Clade(tmpdir, cmds_file, conf=conf).parse("CC")

    with parse_spy(PidGraph) as p, parse_spy(CC) as c:
        Clade(tmpdir, cmds_file, conf=conf).parse("CC")

    assert p.called == force
    assert c.called == force


@pytest.mark.parametrize("clean", [True, False])
def test_parse_clean(tmpdir, cmds_file, clean):
    c = Clade(tmpdir, cmds_file)
    c.parse("CC", clean=clean)

    with parse_spy(PidGraph) as p, parse_spy(CC) as cc:
        c.parse("CC", clean=clean)

    assert cc.called == clean
    assert not p.called


def test_check_conf_consistency(tmpdir, cmds_file):
    conf = {"PidGraph.filter_cmds_by_pid": True}

    c = Clade(tmpdir, cmds_file, conf=conf)
    c.parse("PidGraph")

    changed_conf = {"PidGraph.filter_cmds_by_pid": False}

    c = Clade(tmpdir, cmds_file, conf=changed_conf)
    with pytest.raises(RuntimeError):
        c.parse("CC")


def test_no_empty_ext_dirs(tmpdir, cmds_file):
    c = Clade(tmpdir, cmds_file)
    c.parse("CmdGraph")

    # Extensions that only write to the database get no directory
    assert not os.path.exists(os.path.join(str(tmpdir), "CmdGraph"))
    assert not os.path.exists(os.path.join(str(tmpdir), "PidGraph"))
    assert c.CmdGraph.is_parsed()
    assert c.work_dir_ok()

    c.parse_list(["CmdGraph"], clean=True)
    assert c.CmdGraph.is_parsed()
    assert c.cmd_graph
