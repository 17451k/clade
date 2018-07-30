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


def load_cmds(cmds_file):
    """Open file with intercepted commands.

    Raises:
        RuntimeError: Specified file does not exist or empty
    """
    if not os.path.exists(cmds_file):
        raise RuntimeError("Specified {} file does not exist".format(cmds_file))

    if not os.path.getsize(cmds_file):
        raise RuntimeError("Specified {} file is empty".format(cmds_file))

    cmds_fp = open(cmds_file)

    return cmds_fp


def filter_cmd_by_which_list(cmd, which_list):
    """Filter intercepted command by 'which' field."""
    for which in which_list:
        if cmd["which"] == which:
            return True

    return False


def get_build_cwd(cmds):
    """Get the working directory in which build process occurred."""
    return cmds[0]["cwd"]


def get_last_id(cmds):
    """Get last used id."""
    return cmds[-1]["id"]


def get_stats(cmds):
    """Get statistics of intercepted commands number."""
    stats = dict()
    for cmd in cmds:
        if cmd["which"] in stats:
            stats[cmd["which"]] += 1
        else:
            stats[cmd["which"]] = 1

    return stats


def print_cmds_stats(args=sys.argv[1:]):
    if not args:
        sys.exit("Path to the json file with intercepted commands is missing")

    cmds = load_cmds(args[0])
    stats = get_stats(cmds)

    total_count = sum(stats.values())
    for key in sorted(stats, key=stats.get):
        print("{}: {}".format(stats[key], key))

    print("-------------" + "-" * len(str(total_count)))
    print("Total count: {}".format(total_count))
