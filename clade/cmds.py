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
import re
import sys

DELIMITER = "||"


def open_cmds_file(cmds_file):
    """Open txt file with intercepted commands and return file object.

    Raises:
        RuntimeError: Specified file does not exist or empty.
    """
    if not os.path.exists(cmds_file):
        raise RuntimeError("Specified {} file does not exist".format(cmds_file))
    if not os.path.getsize(cmds_file):
        raise RuntimeError("Specified {} file is empty".format(cmds_file))

    return open(cmds_file)


def iter_cmds_by_which(cmds_fp, which_list):
    """Get an iterator over all intercepted commands filtered by 'which' field.

    Args:
        cmds_fp: A file object.
        which_list: A list of strings to filter command by 'which' field.
    """
    for cmd in iter_cmds(cmds_fp):
        for which in which_list:
            if re.search(which, cmd["which"]):
                yield cmd
                break


def iter_cmds(cmds_fp):
    """Get an iterator over all intercepted commands.

    Args:
        cmds_fp: A file object.
    """
    for cmd_id, line in enumerate(cmds_fp):
        cmd = dict()
        cmd["id"] = str(cmd_id + 1)  # cmd_id should be line number in cmds_fp file
        cmd["cwd"], cmd["pid"], cmd["which"], *cmd["command"] = line.strip().split(DELIMITER)
        cmd["which"] = os.path.normpath(cmd["which"])

        yield cmd


def get_first_cmd(cmds_file):
    """Get first intercepted command."""
    return next(iter_cmds(open_cmds_file(cmds_file)))


def get_build_cwd(cmds_file):
    """Get the working directory in which build process occurred."""
    first_cmd = get_first_cmd(cmds_file)
    return first_cmd["cwd"]


def get_last_cmd(cmds_file):
    """Get last intercepted command."""
    iterable = iter_cmds(open_cmds_file(cmds_file))

    last_cmd = next(iterable)
    for last_cmd in iterable:
        pass

    return last_cmd


def get_last_id(cmds_file):
    """Get last used id."""
    try:
        last_cmd = get_last_cmd(cmds_file)
        return last_cmd["id"]
    except RuntimeError:
        return "0"


def get_all_cmds(cmds_file):
    """Get list of all intercepted build commands."""
    with open_cmds_file(cmds_file) as cmds_fp:
        return list(iter_cmds(cmds_fp))


def get_stats(cmds_file):
    """Get statistics of intercepted commands number."""
    stats = dict()
    with open_cmds_file(cmds_file) as cmds_fp:
        for cmd in iter_cmds(cmds_fp):
            if cmd["which"] in stats:
                stats[cmd["which"]] += 1
            else:
                stats[cmd["which"]] = 1

    return stats


def print_cmds_stats(args=sys.argv[1:]):
    if not args:
        sys.exit("Path to the json file with intercepted commands is missing")

    stats = get_stats(args[0])

    total_count = sum(stats.values())
    for key in sorted(stats, key=stats.get):
        print("{}: {}".format(stats[key], key))

    print("-------------" + "-" * len(str(total_count)))
    print("Total count: {}".format(total_count))
