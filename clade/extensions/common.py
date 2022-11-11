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
import sys

from clade.extensions.abstract import Extension
from clade.extensions.opts import requires_value, requires_mult_values
from clade.cmds import iter_cmds_by_which, number_of_cmds_by_which


def unwrap(self, cmd):
    return self.parse_cmd(cmd)


class Common(Extension, metaclass=abc.ABCMeta):
    """Parent class for CC, LD, MV, AR, AS and Objcopy classes.

    Raises:
        RuntimeError: Command can't be parsed as its type is not supported.
    """

    requires = ["PidGraph", "Path"]

    __version__ = "3"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.raw_dir = "raw"
        self.opts_dir = "opts"
        self.cmds_dir = "cmds"

        self.cmds_file = os.path.join(self.work_dir, "cmds.json")

        self.bad_ids = os.path.join(self.work_dir, "bad_ids.txt")

        exclude_list = self.conf.get("Common.exclude_list", [])
        exclude_list_in = self.conf.get("Common.exclude_list_in", [])
        exclude_list_out = self.conf.get("Common.exclude_list_out", [])
        include_list = self.conf.get("Common.include_list", [])

        self.regex_exclude_in = None
        self.regex_exclude_out = None
        self.regex_include_in = None

        # Make a regex that matches if any of our regexes match.
        if exclude_list or exclude_list_in:
            self.regex_exclude_in = re.compile(
                "(" + ")|(".join(exclude_list + exclude_list_in) + ")"
            )

        if exclude_list or exclude_list_out:
            self.regex_exclude_out = re.compile(
                "(" + ")|(".join(exclude_list + exclude_list_out) + ")"
            )

        if include_list:
            self.regex_include_in = re.compile(
                "(" + ")|(".join(include_list) + ")"
            )

    @Extension.prepare
    def parse(self, cmds_file, which_list):
        """Multiprocess parsing of build commands filtered by 'which' field."""

        total_cmds = number_of_cmds_by_which(cmds_file, which_list)
        cmds = iter_cmds_by_which(cmds_file, which_list)

        if total_cmds:
            self.log(f"Parsing {total_cmds} commands")
            self.execute_in_parallel(cmds, unwrap, total_objs=total_cmds)

        self.__merge_all_cmds()

    def _get_cmd_dict(self, cmd):
        return {
            "id": cmd["id"],
            "in": [],
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": [os.path.normpath(cmd["which"])] + cmd["command"][1:],
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
            # Options with multiple values.
            if opt in requires_mult_values[cmd_type].keys():
                vals = []
                for _ in range(requires_mult_values[cmd_type][opt]):
                    vals.append(next(opts))
                parsed_cmd["opts"].extend([opt] + vals)
            # Options with single values.
            elif opt in requires_value[cmd_type]:
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
        cmd = self._normalize_paths(cmd)
        self.debug("Parsed command {}".format(cmd))

        self.dump_opts_by_id(cmd["id"], cmd["opts"])
        del cmd["opts"]
        self.dump_raw_by_id(cmd["id"], cmd["command"])
        del cmd["command"]

        self.dump_data(cmd, os.path.join(self.cmds_dir, "{}.json".format(id)))

    def load_raw_by_id(self, id):
        raw_file = os.path.join(self.raw_dir, "{}.json".format(id))
        return self.load_data(raw_file, raise_exception=True)

    def dump_raw_by_id(self, id, raw_command):
        self.dump_data(
            raw_command, os.path.join(self.raw_dir, "{}.json".format(id))
        )

    def load_opts_by_id(self, id):
        opts_file = os.path.join(self.opts_dir, "{}.json".format(id))
        opts = self.load_data(opts_file, raise_exception=False)

        # if load_data can't find file, it returns empty dict()
        # but opts must be a list
        return opts if opts else []

    def dump_opts_by_id(self, id, opts):
        # Do not dump options if they are empty
        if not opts:
            return

        self.dump_data(opts, os.path.join(self.opts_dir, "{}.json".format(id)))

    def dump_bad_cmd_id(self, cmd_id):
        os.makedirs(os.path.dirname(self.bad_ids), exist_ok=True)

        with open(self.bad_ids, "a") as fh:
            fh.write("{}\n".format(cmd_id))

    def get_bad_ids(self):
        if not os.path.exists(self.bad_ids):
            return []

        with open(self.bad_ids, "r") as fh:
            return fh.read().splitlines()

    def _normalize_paths(self, cmd):
        if "Path" not in self.extensions:
            self.error("Path extension is not available")
            return cmd

        cmd["in"] = self.extensions["Path"].normalize_rel_paths(cmd["in"], cmd["cwd"])
        cmd["out"] = self.extensions["Path"].normalize_rel_paths(cmd["out"], cmd["cwd"])
        cmd["cwd"] = self.extensions["Path"].normalize_abs_path(cmd["cwd"])

        return cmd

    def __merge_all_cmds(self):
        """Merge all parsed commands into a single json file."""
        self.debug("Merging all parsed commands")
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

        self.dump_data(merged_cmds, self.cmds_file)

    def load_all_cmds(
        self, with_opts=False, with_raw=False, filter_by_pid=True
    ):
        """Load all parsed commands."""
        cmds = self.load_data(self.cmds_file, raise_exception=False)

        if filter_by_pid and self.conf.get(
            "PidGraph.filter_cmds_by_pid", True
        ):
            bad_ids = self.get_bad_ids()
            self.debug("Bad commands: {}".format(bad_ids))
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
                if self.regex_exclude_in and self.regex_exclude_in.search(cmd_in)
            )
        ):
            self.debug("Command {} is bad".format(cmd))
            return True

        if any(
            (
                True
                for cmd_in in cmd_ins
                if self.regex_include_in and not self.regex_include_in.search(cmd_in)
            )
        ):
            self.debug("Command {} is bad".format(cmd))
            return True

        cmd_outs = [os.path.join(cmd["cwd"], cmd_out) for cmd_out in cmd["out"]]
        if any(
            (
                True
                for cmd_out in cmd_outs
                if self.regex_exclude_out and self.regex_exclude_out.search(cmd_out)
            )
        ):
            self.debug("Command {} is bad".format(cmd))
            return True

        return False


# Since Windows has no fork, multiprocessing workers doesnt have access to imported extensions
# WARNING: Do not put this code on top of the file, otherwise there will be import errors due to "circular importing"
if "clade.extensions.compiler" not in sys.modules and sys.platform == "win32":
    Extension._import_extension_modules()
