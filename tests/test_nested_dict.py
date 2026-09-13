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

from clade.types.nested_dict import nested_dict, traverse


def make_dict():
    d = nested_dict()
    d["a"]["b"]["c"] = 1
    d["a"]["x"]["y"] = 2
    d["k"] = 3
    return d


def test_traverse_full_depth():
    d = make_dict()

    # entries shorter than depth 3 (the "k" entry) are dropped by default
    result = sorted(traverse(d, 3))

    assert result == sorted([["a", "b", "c"], ["a", "x", "y"]])


def test_traverse_restrict():
    d = make_dict()

    result = list(traverse(d, 3, restrict={2: "b"}))

    assert result == [["a", "b", "c"]]


def test_traverse_allow_smaller():
    d = make_dict()

    result = sorted(traverse(d, 3))
    assert ["k", 3] not in result

    result_smaller = sorted(traverse(d, 3, allow_smaller=True), key=str)
    assert (
        sorted([["a", "b", "c"], ["a", "x", "y"], ["k", 3]], key=str) == result_smaller
    )


def test_traverse_zero_depth():
    d = make_dict()

    assert list(traverse(d, 0)) == []
