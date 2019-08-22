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

import collections


def nested_dict():
    return collections.defaultdict(nested_dict)


def traverse(ndict, depth, restrict=None, allow_smaller=False):
    """Traverse nested dictionary and yield list of its elements.

    Args:
        depth: limit depth of the dictionary to traverse.
        restrict: ability to restrict output by specifying the exact value
                  that must be at a specified position of the output list.
                  Example: restrict={3: "calls"}.
        allow_smaller: allow to return list of the size smaller then required
                       (if the dictionary is not uniform).
    """

    if not restrict:
        restrict = dict()

    for l in __traverse(ndict, depth):
        if not restrict:
            if allow_smaller or len(l) == depth:
                yield l
            continue

        allow = True

        for key in restrict:
            if key <= len(l) and l[key - 1] != restrict[key]:
                allow = False

        if allow and (allow_smaller or len(l) == depth):
            yield l


def __traverse(ndict, depth):
    if depth == 0:
        return []

    if not isinstance(ndict, dict):
        yield [ndict]
        return

    for key in ndict:
        r = False

        for l in __traverse(ndict[key], depth - 1):
            yield [key] + l
            r = True

        if not r:
            yield [key]
