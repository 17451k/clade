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

import collections
import os


def nested_dict():
    return collections.defaultdict(nested_dict)


def normalize_path(path, cwd):
    abs_path = os.path.abspath(path)

    if os.path.commonprefix([abs_path, cwd]) == cwd:
        return os.path.relpath(abs_path, start=cwd)
    else:
        return os.path.normpath(path)
