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

from clade.extensions.utils import yield_chunk
from clade.utils import get_clade_version, get_program_version, merge_preset_to_conf


def test_get_clade_version():
    version = get_clade_version()

    assert version
    assert type(version) == str


def test_get_program_version():
    version = get_program_version("gcc")

    assert version
    assert type(version) == str
    assert get_clade_version() in get_program_version("clade")


def test_merge_preset_to_conf():
    conf = {}

    assert merge_preset_to_conf("klever_linux_kernel", conf)


def test_yield_chunk():
    assert list(yield_chunk(range(5), chunk_size=2)) == [[0, 1], [2, 3], [4]]
    assert list(yield_chunk([], 2)) == []
