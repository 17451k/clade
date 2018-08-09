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

import glob
import multiprocessing
import os
import re
import shutil

from clade.extensions.abstract import Extension
from clade.extensions.utils import normalize_path
from clade.cmds import iter_cmds_by_which, open_cmds_file

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
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        super().__init__(work_dir, conf)

        cmd_filter = self.conf.get("Common.filter", [])
        cmd_filter_in = self.conf.get("Common.filter_in", [])
        cmd_filter_out = self.conf.get("Common.filter_out", [])

        # Make a regex that matches if any of our regexes match.
        self.regex_in = re.compile("(" + ")|(".join(cmd_filter + cmd_filter_in) + ")")
        self.regex_out = re.compile("(" + ")|(".join(cmd_filter + cmd_filter_out) + ")")

    def parse(self, cmds_file, which_list):
        """Multiprocess parsing of build commands filtered by 'which' field."""
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.log("Start parsing")

        class CmdWorker(multiprocessing.Process):
            def __init__(self, cmds_queue, ext):
                super().__init__()
                self.cmds_queue = cmds_queue
                self.ext = ext

            def run(self):
                for cmd in iter(self.cmds_queue.get, None):
                    self.ext.parse_cmd(cmd)

        cmds_queue = multiprocessing.Queue()
        cmd_workers = []
        cmd_workers_num = os.cpu_count()

        for i in range(cmd_workers_num):
            cmd_worker = CmdWorker(cmds_queue, self)
            cmd_workers.append(cmd_worker)
            cmd_worker.start()

        with open_cmds_file(cmds_file) as cmds_fp:
            for cmd in iter_cmds_by_which(cmds_fp, which_list):
                cmds_queue.put(cmd)

        # Terminate all workers.
        for i in range(cmd_workers_num):
            cmds_queue.put(None)

        # Wait for all workers do finish their operation
        for i in range(cmd_workers_num):
            cmd_workers[i].join()

        self.__merge_all_cmds()

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

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

    def __merge_all_cmds(self):
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
            return self.__merge_all_cmds()

    def is_bad(self, cmd):
        for _ in (cmd_in for cmd_in in cmd["in"] if self.regex_in.match(cmd_in)):
            return True

        if cmd["out"] and self.regex_out.match(cmd["out"]):
            return True

        return False
