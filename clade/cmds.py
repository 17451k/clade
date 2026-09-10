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
from collections.abc import Generator
from typing import TextIO, TypedDict

DELIMITER = "||"


# "in" is a keyword, so the functional form is required
ParsedCmd = TypedDict(
    "ParsedCmd",
    {
        "id": int,
        "in": list[str],
        "out": list[str],
        "opts": list[str],
        "cwd": str,
        "command": list[str],
        "deps": list[str],
        "type": str,
    },
    total=False,
)


class Cmd(TypedDict):
    id: int
    cwd: str
    pid: int
    which: str
    command: list[str]


def open_cmds_file(cmds_file: str) -> TextIO:
    """Open txt file with intercepted commands and return file object.

    Raises:
        RuntimeError: Specified file does not exist or empty.
    """
    if not os.path.exists(cmds_file):
        raise RuntimeError(f"Specified {cmds_file} file does not exist")
    if not os.path.getsize(cmds_file):
        raise RuntimeError(f"Specified {cmds_file} file is empty")

    return open(cmds_file)


def iter_cmds_by_which(
    cmds_file: str, which_list: list[str]
) -> Generator[Cmd, None, None]:
    """Get an iterator over all intercepted commands filtered by 'which' field.

    Args:
        cmds_file: Path to the txt file with intercepted commands.
        which_list: A list of strings to filter command by 'which' field.
    """
    for cmd in iter_cmds(cmds_file):
        for which in which_list:
            if re.search(which, cmd["which"]):
                yield cmd
                break


def number_of_cmds_by_which(cmds_file: str, which_list: list[str]) -> int:
    """Return number of all intercepted commands filtered by 'which' field.

    Args:
        cmds_file: Path to the txt file with intercepted commands.
        which_list: A list of strings to filter command by 'which' field.
    """

    i = 0

    for _ in iter_cmds_by_which(cmds_file, which_list):
        i += 1

    return i


def iter_cmds(cmds_file: str) -> Generator[Cmd, None, None]:
    """Get an iterator over all intercepted commands.

    Args:
        cmds_file: Path to the txt file with intercepted commands.
    """
    with open_cmds_file(cmds_file) as cmds_fp:
        for cmd_id, line in enumerate(cmds_fp):
            # cmd_id should be line number in cmds_fp file
            yield split_cmd(line, cmd_id + 1)


def split_cmd(line: str, cmd_id: int = 0) -> Cmd:
    """Convert a single intercepted command into dictionary."""
    cwd, pid, which, *command = line.strip().split(DELIMITER)
    return {
        "id": cmd_id,
        "cwd": cwd,
        "pid": int(pid),
        "which": which,
        "command": command,
    }


def join_cmd(cmd: Cmd) -> str:
    """Convert a single intercepted command from dictionary to cmds.txt line."""
    line = DELIMITER.join([cmd["cwd"], str(cmd["pid"]), cmd["which"]] + cmd["command"])
    return line


def get_first_cmd(cmds_file: str) -> Cmd:
    """Get first intercepted command."""
    return next(iter_cmds(cmds_file))


def get_build_dir(cmds_file: str) -> str:
    """Get the working directory in which build process occurred."""
    first_cmd = get_first_cmd(cmds_file)
    return first_cmd["cwd"]


def get_last_cmd(cmds_file: str) -> Cmd:
    """Get last intercepted command."""
    iterable = iter_cmds(cmds_file)

    last_cmd = next(iterable)
    for last_cmd in iterable:
        pass

    return last_cmd


def get_last_id(cmds_file: str, raise_exception: bool = False) -> int:
    """Get last used id."""
    try:
        last_cmd = get_last_cmd(cmds_file)
        return last_cmd["id"]
    except RuntimeError:
        if raise_exception:
            raise
        return 0


def get_all_cmds(cmds_file: str) -> list[Cmd]:
    """Get list of all intercepted build commands."""
    return list(iter_cmds(cmds_file))


def get_stats(cmds_file: str) -> dict[str, int]:
    """Get statistics of intercepted commands number."""
    stats = {}
    for cmd in iter_cmds(cmds_file):
        if cmd["which"] in stats:
            stats[cmd["which"]] += 1
        else:
            stats[cmd["which"]] = 1

    return stats
