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


def normalize_path(path, cwd, cache=dict()):
    # Cache variable considerably speeds up normalizing.
    # Cache size is quite small even for extra large files.

    if cwd not in cache:
        cache[cwd] = dict()

    if path in cache[cwd]:
        return cache[cwd][path]

    abs_path = os.path.abspath(path)

    if os.path.commonprefix([abs_path, cwd]) == cwd:
        cache[cwd][path] = os.path.relpath(abs_path, start=cwd)
    else:
        cache[cwd][path] = os.path.normpath(path)

    return cache[cwd][path]
