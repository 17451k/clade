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

import hashlib
import itertools

def get_string_hash(key):
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def yield_chunk(container, chunk_size=1000):
    it = iter(container)

    while True:
        piece = list(itertools.islice(it, chunk_size))

        if piece:
            yield piece
        else:
            return
