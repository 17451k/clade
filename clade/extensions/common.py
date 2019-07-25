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

import abc
import glob
import os
import re
import shutil
import sys

from clade.extensions.abstract import Extension
from clade.extensions.opts import requires_value
from clade.cmds import iter_cmds_by_which, number_of_cmds_by_which


def unwrap(self, cmd):
    return self.parse_cmd(cmd)


class Common(Extension, metaclass=abc.ABCMeta):
    """Parent class for CC, LD, MV, AR, AS and Objcopy classes.

    Raises:
        RuntimeError: Command can't be parsed as its type is not supported.
    """

    requires = ["PidGraph"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.raw_dir = "raw"
        self.opts_dir = "opts"
        self.cmds_dir = "cmds"
        self.bad_dir = "bad"

        cmd_filter = self.conf.get("Common.filter", [])
        cmd_filter_in = self.conf.get("Common.filter_in", [])
        cmd_filter_out = self.conf.get("Common.filter_out", [])

        self.regex_in = None
        self.regex_out = None

        # Make a regex that matches if any of our regexes match.
        if cmd_filter or cmd_filter_in:
            self.regex_in = re.compile(
                "(" + ")|(".join(cmd_filter + cmd_filter_in) + ")"
            )

        if cmd_filter or cmd_filter_out:
            self.regex_out = re.compile(
                "(" + ")|(".join(cmd_filter + cmd_filter_out) + ")"
            )

    @Extension.prepare
    def parse(self, cmds_file, which_list):
        """Multiprocess parsing of build commands filtered by 'which' field."""

        total_cmds = number_of_cmds_by_which(cmds_file, which_list)
        cmds = iter_cmds_by_which(cmds_file, which_list)
        self.parse_cmds_in_parallel(cmds, unwrap, total_cmds=total_cmds)

        self.__merge_all_cmds()

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def __terminate_workers(self, cmds_queue, cmd_workers, cmd_workers_num):
        # Terminate all workers.
        for i in range(cmd_workers_num):
            cmds_queue.put(None)

        # Wait for all workers do finish their operation
        for i in range(cmd_workers_num):
            cmd_workers[i].join()

    def _get_cmd_dict(self, cmd):
        return {
            "id": cmd["id"],
            "in": [],
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"],
        }

    def parse_cmd(self, cmd, cmd_type):
        """Parse single build command."""
        self.debug("Parse: {}".format(cmd))
        parsed_cmd = self._get_cmd_dict(cmd)

        if cmd_type not in requires_value:
            raise RuntimeError(
                "Command type '{}' is not supported".format(cmd_type)
            )

        opts = iter(cmd["command"][1:])

        for opt in opts:
            # Options with values.
            if opt in requires_value[cmd_type]:
                # Value is the next option.
                val = next(opts)
                if opt == "-o":
                    parsed_cmd["out"].append(os.path.normpath(val))
                else:
                    parsed_cmd["opts"].extend([opt, val])
            # Options without values
            # Or with values that are not separated by space
            elif re.search(r"^-", opt):
                parsed_cmd["opts"].append(opt)
            # Input files are not options and not values of other options
            else:
                parsed_cmd["in"].append(opt)

        return parsed_cmd

    def load_cmd_by_id(self, id):
        return self.load_data(
            os.path.join(self.cmds_dir, "{}.json".format(id))
        )

    def dump_cmd_by_id(self, id, cmd):
        self.dump_opts_by_id(cmd["id"], cmd["opts"])
        del cmd["opts"]
        self.dump_raw_by_id(cmd["id"], cmd["command"])
        del cmd["command"]

        self.dump_data(cmd, os.path.join(self.cmds_dir, "{}.json".format(id)))

    def load_raw_by_id(self, id):
        raw_file = os.path.join(self.raw_dir, "{}.json".format(id))
        return self.load_data(raw_file, raise_exception=False)

    def dump_raw_by_id(self, id, raw_command):
        self.dump_data(
            raw_command, os.path.join(self.raw_dir, "{}.json".format(id))
        )

    def load_opts_by_id(self, id):
        opts_file = os.path.join(self.opts_dir, "{}.json".format(id))
        return self.load_data(opts_file, raise_exception=False)

    def dump_opts_by_id(self, id, opts):
        self.dump_data(opts, os.path.join(self.opts_dir, "{}.json".format(id)))

    def dump_bad_cmd_by_id(self, id, cmd):
        self.dump_opts_by_id(cmd["id"], cmd["opts"])
        del cmd["opts"]
        self.dump_raw_by_id(cmd["id"], cmd["command"])
        del cmd["command"]

        self.dump_data(cmd, os.path.join(self.bad_dir, "{}.json".format(id)))

    def load_bad_cmd_by_id(self, id):
        # Warning: bad commands do not have dependencies
        return self.load_data(os.path.join(self.bad_dir, "{}.json".format(id)))

    def get_bad_ids(self):
        cmd_jsons = glob.glob(
            os.path.join(self.work_dir, self.bad_dir, "*[0-9].json")
        )

        return [
            os.path.splitext(os.path.basename(cmd_json))[0]
            for cmd_json in cmd_jsons
        ]

    def __merge_all_cmds(self):
        """Merge all parsed commands into a single json file."""
        cmd_jsons = glob.glob(
            os.path.join(self.work_dir, self.cmds_dir, "*[0-9].json")
        )

        merged_cmds = []

        for cmd_json in cmd_jsons:
            parsed_cmd = self.load_data(cmd_json)
            merged_cmds.append(parsed_cmd)

        if not merged_cmds:
            self.debug("No commands were parsed")
            return

        self.dump_data(merged_cmds, "cmds.json")

    def load_all_cmds(
        self, with_opts=False, with_raw=False, filter_by_pid=True
    ):
        """Load all parsed commands."""
        cmds = self.load_data("cmds.json", raise_exception=False)

        if filter_by_pid and self.conf.get(
            "PidGraph.filter_cmds_by_pid", True
        ):
            bad_ids = self.get_bad_ids()
            cmds = self.extensions["PidGraph"].filter_cmds_by_pid(cmds, parsed_ids=bad_ids)

        if with_opts:
            for cmd in cmds:
                if "opts" not in cmd:
                    cmd["opts"] = self.load_opts_by_id(cmd["id"])

        if with_raw:
            for cmd in cmds:
                if "command" not in cmd:
                    cmd["command"] = self.load_raw_by_id(cmd["id"])

        return cmds

    def is_bad(self, cmd):
        cmd_ins = [os.path.join(cmd["cwd"], cmd_in) for cmd_in in cmd["in"]]
        if any(
            (
                True
                for cmd_in in cmd_ins
                if self.regex_in and self.regex_in.search(cmd_in)
            )
        ):
            return True

        cmd_outs = [os.path.join(cmd["cwd"], cmd_out) for cmd_out in cmd["out"]]
        if any(
            (
                True
                for cmd_out in cmd_outs
                if self.regex_out and self.regex_out.search(cmd_out)
            )
        ):
            return True

        return False


# Since Windows has no fork, multiprocessing workers doesnt have access to imported extensions
# WARNING: Do not put this code on top of the file, otherwise there will be import errors due to "circular importing"
if "clade.extensions.compiler" not in sys.modules and sys.platform == "win32":
    Extension._import_extension_modules()
