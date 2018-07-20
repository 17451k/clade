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
import sys
import ujson


class Cmds():
    """Interface object for working with intercepted commands.

    In case of really large jsons object creation may take some time
    and consume several gigabytes of RAM

    Attributes:
        cmds_json: A path to the json file where intercepted commands is stored

    Raises:
        RuntimeError: Specified json file does not exist or empty
    """

    def __init__(self, cmds_json):
        if not os.path.exists(cmds_json):
            raise RuntimeError("Specified {} json file does not exist".format(cmds_json))

        with open(cmds_json, "r") as f:
            self.cmds = ujson.load(f)

        if not self.cmds:
            raise RuntimeError("Specified {} json file is empty".format(cmds_json))

    def get_all_cmds(self):
        """Get all intercepted commands."""
        return self.cmds

    def get_cmds_by_which(self, which):
        """Get intercepted commands filtered by 'which' field."""
        return [x for x in self.cmds if x["which"] == which]

    def get_build_cwd(self):
        """Get the working directory in which build process occurred."""
        return self.cmds[0]["cwd"]

    def get_stats(self):
        """Get statistics of intercepted commands number."""
        stats = dict()
        for cmd in self.cmds:
            if cmd["which"] in stats:
                stats[cmd["which"]] += 1
            else:
                stats[cmd["which"]] = 1

        return stats


def print_cmds_stats(args=sys.argv[1:]):
    if not args:
        sys.exit("Path to the json file with intercepted commands is missing")

    c = Cmds(args[0])
    stats = c.get_stats()

    total_count = sum(stats.values())
    for key in sorted(stats, key=stats.get):
        print("{}: {}".format(stats[key], key))

    print("-------------" + "-" * len(str(total_count)))
    print("Total count: {}".format(total_count))
