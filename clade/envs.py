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


def open_envs_file(envs_file):
    """Open txt file with intercepted environment variables and return file object.

    Raises:
        RuntimeError: Specified file does not exist or empty.
    """
    if not os.path.exists(envs_file):
        raise RuntimeError("Specified {} file does not exist".format(envs_file))
    if not os.path.getsize(envs_file):
        raise RuntimeError("Specified {} file is empty".format(envs_file))

    return open(envs_file)


def iter_envs(envs_file):
    """Get an iterator over all intercepted environment variables.

    Args:
        envs_file: Path to the txt file with intercepted environment variables.
    """
    with open_envs_file(envs_file) as envs_fp:
        cmd_id = 1
        envs = {"id": str(cmd_id), "envs": dict()}
        for line in envs_fp:
            if line.strip():
                e = split_env(line)
                envs['envs'].update(e)
            else:
                yield envs
                cmd_id += 1
                envs = {"id": str(cmd_id), "envs": dict()}


def split_env(line):
    """Convert a single intercepted environment variable into dictionary."""
    env = dict()
    l = line.strip().split('=', maxsplit=1)
    env[l[0]] = l[1]
    return env


def join_env(env):
    """Convert a single intercepted environment variable from dictionary to envs.txt line."""
    line = '='.join(list(env.items())[0])
    return line


def get_first_env(envs_file):
    """Get environment variables for first intercepted command."""
    return next(iter_envs(envs_file))


def get_last_env(envs_file):
    """Get environment variables for last intercepted command."""
    iterable = iter_envs(envs_file)

    last_env = next(iterable)
    for last_env in iterable:
        pass

    return last_env


def get_last_id(envs_file, raise_exception=False) -> str:
    """Get last used id."""
    try:
        last_env = get_last_env(envs_file)
        return last_env["id"]
    except RuntimeError:
        if raise_exception:
            raise
        return "0"


def get_all_envs(envs_file):
    """Get list of all intercepted environment variables."""
    return list(iter_envs(envs_file))


def get_stats(envs_file):
    """Get statistics of intercepted environment variables number."""
    stats = dict()
    for env in iter_envs(envs_file):
        stats[env["id"]] = len(env['envs'])

    return stats
