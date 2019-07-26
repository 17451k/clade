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

import sys


from clade.cmds import get_stats


def print_cmds_stats(args=sys.argv[1:]):
    if not args:
        sys.exit("Path to the json file with intercepted commands is missing")

    stats = get_stats(args[0])

    total_count = sum(stats.values())
    for key in sorted(stats, key=stats.get):
        print("{}: {}".format(stats[key], key))

    print("-------------" + "-" * len(str(total_count)))
    print("Total count: {}".format(total_count))
