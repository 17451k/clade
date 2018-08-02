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

import argparse
import glob
import multiprocessing
import os
import re
import shutil

from clade.extensions.abstract import Extension
from clade.extensions.utils import normalize_path
from clade.cmds import filter_cmds_by_which_list

opts_info = {
    "CC": {
        "require_values": (
            "-D",
            "-I",
            "-O",
            "-include",
            "-isystem",
            "-mcmodel",
            "-o",
            "-print-file-name",
            "-x",
            "-idirafter",
            "-MT",
            "-MF",
            "-MQ",
            "asan-stack",
            "asan-globals",
            "asan-instrumentation-with-call-threshold",
        )
    },
    "LD": {
        "require_values": (
            "-T",
            "-m",
            "-o"
        )
    },
    "Objcopy": {
        "require_values": (
            "--set-section-flags",
            "--rename-section",
            "-O"
        )
    }
}


class Common(Extension):
    """Parent class for CC, LD and Objcopy classes.

    Raises:
        RuntimeError: Command can't be parsed as its type is not supported.
    """

    def parse(self, cmds, which_list, f):
        """Multiprocess parsing of build commands filtered by 'which' field."""
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.log("Start parsing")

        filtered_cmds = filter_cmds_by_which_list(cmds, which_list)

        with multiprocessing.Pool(os.cpu_count()) as p:
            p.map(f, zip([self] * len(filtered_cmds), filtered_cmds))

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        self.merge_all_cmds()

        self.log("Parsing finished")

    def parse_cmd(self, cmd, cmd_type):
        """Parse single bulid command."""
        self.debug("Parse: {}".format(cmd))
        parsed_cmd = {
            "id": cmd["id"],
            "in": [],
            "out": None,
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"][0]
        }

        if cmd_type not in opts_info:
            raise RuntimeError("Command type '{}' is not supported".format(cmd_type))

        opts = iter(cmd["command"][1:])

        for opt in opts:
            # Options with values.
            match = None
            for opt_requiring_val in opts_info[cmd_type]["require_values"]:
                match = re.search(r"^({})(=?)(.*)".format(opt_requiring_val), opt)
                if match:
                    opt, eq, val = match.groups()

                    # Option value is specified by means of the following option.
                    if not val:
                        val = next(opts)
                        if opt != "-o":
                            parsed_cmd["opts"].extend(["{}".format(opt), val])
                            break

                    if opt == "-o":
                        parsed_cmd["out"] = os.path.normpath(val)
                    else:
                        parsed_cmd["opts"].append("{}{}{}".format(opt, eq, val))

                    break

            if not match:
                # Options without values.
                if re.search(r"^-.+$", opt):
                    parsed_cmd["opts"].append(opt)
                # Input files.
                else:
                    parsed_cmd["in"].append(os.path.normpath(opt))

        if parsed_cmd["out"]:
            parsed_cmd["out"] = normalize_path(parsed_cmd["out"], parsed_cmd["cwd"])

        return parsed_cmd

    def load_cmd_by_id(self, id):
        return self.load_data("{}.json".format(id))

    def dump_cmd_by_id(self, id, cmd):
        self.dump_data(cmd, "{}.json".format(id))

    def load_opts_by_id(self, id):
        return self.load_data("{}-opts.json".format(id))

    def dump_opts_by_id(self, id, opts):
        self.dump_data(opts, "{}-opts.json".format(id))

    def load_deps_by_id(self, id):
        return self.load_data("{}-deps.json".format(id))

    def dump_deps_by_id(self, id, deps):
        self.dump_data(deps, "{}-deps.json".format(id))

    def merge_all_cmds(self):
        """Merge all parsed commands into a single json file."""
        cmd_jsons = glob.glob(os.path.join(self.work_dir, '*[0-9].json'))

        merged_cmds = []

        for cmd_json in cmd_jsons:
            parsed_cmd = self.load_data(cmd_json)
            merged_cmds.append(parsed_cmd)

        if not merged_cmds:
            raise RuntimeError("No parsed commands found")

        self.dump_data(merged_cmds, "all.json")

    def load_all_cmds(self):
        """Load all parsed commands."""
        try:
            return self.load_data("all.json")
        except FileNotFoundError:
            return self.merge_all_cmds()


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-w", "--work_dir", help="a path to the DIR where processed commands will be saved", metavar='DIR', default="clade")
    parser.add_argument("-l", "--log_level", help="set logging level (ERROR, INFO, or DEBUG)", default="ERROR")
    parser.add_argument(dest="cmds_json", help="a path to the file with intercepted commands")

    args = parser.parse_args(args)

    return args
