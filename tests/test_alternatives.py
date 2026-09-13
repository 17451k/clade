# Copyright (c) 2026 Ilya Shchepetkov
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

from clade import Clade
from clade.intercept import intercept


def test_alternatives(tmpdir):
    src = tmpdir / "a.txt"
    src.write_text("hello", encoding="utf-8")
    link = tmpdir / "b.txt"
    cmds_file = tmpdir / "cmds.txt"

    intercept(
        command=["ln", "-s", "a.txt", "b.txt"],
        cwd=str(tmpdir),
        output=str(cmds_file),
    )

    c = Clade(
        str(tmpdir / "work"),
        str(cmds_file),
        conf={
            "Alternatives.requires": ["LN"],
            "Alternatives.use_canonical_paths": True,
        },
    )
    e = c.parse("Alternatives")
    alts = e.load_alternatives()

    src_path = os.path.realpath(str(src))
    link_path = os.path.realpath(str(link))

    norm_alts = {
        os.path.realpath(k): [os.path.realpath(v) for v in vals]
        for k, vals in alts.items()
    }

    assert link_path in norm_alts
    assert src_path in norm_alts[link_path]

    assert src_path in norm_alts
    assert link_path in norm_alts[src_path]

    assert os.path.realpath(c.get_canonical_path(str(link))) == os.path.realpath(
        c.get_canonical_path(str(src))
    )
    assert c.get_canonical_path("/nonexistent") == "/nonexistent"
    assert Clade(str(tmpdir / "empty")).get_canonical_path("/x") == "/x"
