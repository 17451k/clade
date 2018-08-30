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
import sys

from clade.extensions.abstract import Extension
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
            "-triple",
            "-main-file-name",
            "-mrelocation-model",
            "-pic-level",
            "-mthread-model",
            "-target-cpu",
            "-target-linker-version",
            "-coverage-notes-file",
            "-resource-dir",
            "-fdebug-compilation-dir",
            "-ferror-limit",
            "-fmessage-length",
            "-stack-protector",
            "-imultiarch",
            "-target",
            "-iwithprefix",
            "-dumpbase"
        )
    },
    "LD": {
        "require_values": (
            "-T",
            "-m",
            "-o",
            "-z",
            "-arch",
            "-macosx_version_min",
            "-lto_library"
        )
    },
    "AS": {
        "require_values": (
            "-I",
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

        self.cmds_dir = "cmds"
        self.opts_dir = "opts"
        self.unparsed_dir = "unparsed"

        cmd_filter = self.conf.get("Common.filter")
        cmd_filter_in = self.conf.get("Common.filter_in")
        cmd_filter_out = self.conf.get("Common.filter_out")

        self.regex_in = None
        self.regex_out = None

        # Make a regex that matches if any of our regexes match.
        if cmd_filter or cmd_filter_in:
            self.regex_in = re.compile("(" + ")|(".join(cmd_filter + cmd_filter_in) + ")")

        if cmd_filter or cmd_filter_out:
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
                    if self.ext.conf.get("Common.save_unparsed_cmd", False):
                        file = os.path.join(self.ext.unparsed_dir, "{}.json".format(cmd["id"]))
                        self.ext.dump_data(cmd, file)
                    self.ext.parse_cmd(cmd)

        cmds_queue = multiprocessing.Queue()
        cmd_workers = []
        cmd_workers_num = os.cpu_count()

        for _ in range(cmd_workers_num):
            cmd_worker = CmdWorker(cmds_queue, self)
            cmd_workers.append(cmd_worker)
            cmd_worker.start()

        try:
            with open_cmds_file(cmds_file) as cmds_fp:
                for cmd in iter_cmds_by_which(cmds_fp, which_list):
                    cmds_queue.put(cmd)
        except RuntimeError as e:
            self.__terminate_workers(cmds_queue, cmd_workers, cmd_workers_num)
            self.error(e)
            sys.exit(-1)

        self.__terminate_workers(cmds_queue, cmd_workers, cmd_workers_num)

        self.__merge_all_cmds()

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        self.log("Parsing finished")

    def __terminate_workers(self, cmds_queue, cmd_workers, cmd_workers_num):
        # Terminate all workers.
        for i in range(cmd_workers_num):
            cmds_queue.put(None)

        # Wait for all workers do finish their operation
        for i in range(cmd_workers_num):
            cmd_workers[i].join()

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
            for opt_requiring_val in opts_info[cmd_type]["require_values"]:
                # Options with value specified after "="
                if re.search(r"^{}=.+$".format(opt_requiring_val), opt):
                    parsed_cmd["opts"].append(opt)
                    break
                elif opt_requiring_val == opt:
                    # Option value is specified by means of the following option.
                    val = next(opts)
                    if opt != "-o":
                        parsed_cmd["opts"].extend([opt, val])
                        break

                    if opt == "-o":
                        parsed_cmd["out"] = os.path.normpath(val)
                    else:
                        parsed_cmd["opts"].append(opt)

                    break
            # Options without values.
            else:
                if re.search(r"^-.+$", opt):
                    parsed_cmd["opts"].append(opt)
                # Input files.
                else:
                    parsed_cmd["in"].append(opt)

        return parsed_cmd

    def load_cmd_by_id(self, id):
        return self.load_data(os.path.join(self.cmds_dir, "{}.json".format(id)))

    def dump_cmd_by_id(self, id, cmd):
        self.dump_opts_by_id(cmd["id"], cmd["opts"])
        del cmd["opts"]
        self.dump_data(cmd, os.path.join(self.cmds_dir, "{}.json".format(id)))

    def load_opts_by_id(self, id):
        return self.load_data(os.path.join(self.opts_dir, "{}-opts.json".format(id)))

    def dump_opts_by_id(self, id, opts):
        self.dump_data(opts, os.path.join(self.opts_dir, "{}-opts.json".format(id)))

    def __merge_all_cmds(self):
        """Merge all parsed commands into a single json file."""
        cmd_jsons = glob.glob(os.path.join(self.work_dir, self.cmds_dir, "*[0-9].json"))

        merged_cmds = []

        for cmd_json in cmd_jsons:
            parsed_cmd = self.load_data(cmd_json)
            merged_cmds.append(parsed_cmd)

        for cmd in merged_cmds:
            if self.conf.get("Common.with_opts", True):
                cmd["opts"] = self.load_opts_by_id(cmd["id"])

        if not merged_cmds:
            self.warning("Not commands were parsed")

        self.dump_data(merged_cmds, "cmds.json")

    def load_all_cmds(self):
        """Load all parsed commands."""
        return self.load_data("cmds.json")

    def is_bad(self, cmd):
        for _ in (cmd_in for cmd_in in cmd["in"] if self.regex_in and self.regex_in.match(cmd_in)):
            return True

        if cmd["out"] and self.regex_out and self.regex_out.match(cmd["out"]):
            return True

        return False
