# Copyright (c) 2020 ISP RAS (http://www.ispras.ru)
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

from clade.types.path_tree import PathTree


def test_path_tree():
    pt = PathTree()

    pt[__file__] = 1
    assert __file__ in pt
    assert pt[__file__] == 1
    assert pt.keys() == [__file__]
    assert pt.get(__file__) == 1
    assert not pt.get("do/not/exist")
    assert pt.get("do/not/exist", 2) == 2

    for key in pt:
        assert key == __file__
