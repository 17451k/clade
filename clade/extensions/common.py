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
import multiprocessing
import os
import re
import shutil
import sys

from clade.extensions.abstract import Extension
from clade.extensions.opts import requires_value, preprocessor_deps_opts
from clade.cmds import iter_cmds_by_which, open_cmds_file


class Common(Extension, metaclass=abc.ABCMeta):
    """Parent class for CC, LD and Objcopy classes.

    Raises:
        RuntimeError: Command can't be parsed as its type is not supported.
    """

    requires = ["PidGraph"]

    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        self.cmds_dir = "cmds"
        self.opts_dir = "opts"
        self.unparsed_dir = "unparsed"

        cmd_filter = self.conf.get("Common.filter", [])
        cmd_filter_in = self.conf.get("Common.filter_in", [])
        cmd_filter_out = self.conf.get("Common.filter_out", [])

        self.regex_in = None
        self.regex_out = None

        # Make a regex that matches if any of our regexes match.
        if cmd_filter or cmd_filter_in:
            self.regex_in = re.compile("(" + ")|(".join(cmd_filter + cmd_filter_in) + ")")

        if cmd_filter or cmd_filter_out:
            self.regex_out = re.compile("(" + ")|(".join(cmd_filter + cmd_filter_out) + ")")

    @Extension.prepare
    def parse(self, cmds_file, which_list):
        """Multiprocess parsing of build commands filtered by 'which' field."""
        self.log("Start parsing")

        class CmdWorker(multiprocessing.Process):
            def __init__(self, cmds_queue, ext):
                super().__init__()
                self.cmds_queue = cmds_queue
                self.ext = ext

            def run(self):
                for cmd in iter(self.cmds_queue.get, None):
                    if self.ext.conf.get("Common.save_unparsed_cmds", False):
                        self.ext.dump_unparsed_by_id(cmd["id"], cmd)
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
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"][0]
        }

        if cmd_type not in requires_value:
            raise RuntimeError("Command type '{}' is not supported".format(cmd_type))

        opts = iter(cmd["command"][1:])

        for opt in opts:
            # Options with values.
            if opt in requires_value[cmd_type]:
                # Option value is specified by means of the following option.
                val = next(opts)
                if opt == "-o":
                    parsed_cmd["out"].append(os.path.normpath(val))
                else:
                    parsed_cmd["opts"].extend([opt, val])
            # Options without values (or with values that are not separated by space).
            elif re.search(r"^-", opt):
                parsed_cmd["opts"].append(opt)
            # Input files.
            else:
                parsed_cmd["in"].append(opt)

        if cmd_type == "CC" and not parsed_cmd["out"] and "-c" in parsed_cmd["opts"]:
            for cmd_in in parsed_cmd["in"]:
                # Output file is located inside "cwd" directory, not near cmd_in
                # For example, gcc -c work/1.c will produce 1.o file, not work/1.o
                cmd_out = os.path.join(parsed_cmd["cwd"], os.path.basename(os.path.splitext(cmd_in)[0] + ".o"))
                parsed_cmd["out"].append(cmd_out)

        return parsed_cmd

    def load_cmd_by_id(self, id):
        return self.load_data(os.path.join(self.cmds_dir, "{}.json".format(id)))

    def dump_cmd_by_id(self, id, cmd):
        self.dump_opts_by_id(cmd["id"], cmd["opts"])
        del cmd["opts"]
        self.dump_data(cmd, os.path.join(self.cmds_dir, "{}.json".format(id)))

    def load_opts_by_id(self, id):
        return self.load_data(os.path.join(self.opts_dir, "{}.json".format(id)), raise_exception=False)

    def dump_opts_by_id(self, id, opts):
        self.dump_data(opts, os.path.join(self.opts_dir, "{}.json".format(id)))

    def load_unparsed_by_id(self, id):
        return self.load_data(os.path.join(self.unparsed_dir, "{}.json".format(id)), raise_exception=False)

    def dump_unparsed_by_id(self, id, cmd):
        self.dump_data(cmd, os.path.join(self.unparsed_dir, "{}.json".format(id)))

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
            self.warning("No commands were parsed")

        self.dump_data(merged_cmds, "cmds.json")

    def load_all_cmds(self, filter_by_pid=True):
        """Load all parsed commands."""
        cmds = self.load_data("cmds.json")

        if filter_by_pid and self.conf.get("PidGraph.filter_cmds_by_pid", True):
            return self.extensions["PidGraph"].filter_cmds_by_pid(cmds)

        return cmds

    def is_bad(self, cmd):
        for _ in (cmd_in for cmd_in in cmd["in"] if self.regex_in and self.regex_in.match(cmd_in)):
            return True

        for _ in (cmd_out for cmd_out in cmd["out"] if self.regex_out and self.regex_out.match(cmd_out)):
            return True

        if self.name == "CC" and self.conf.get("CC.filter_deps", True) and set(cmd["opts"]).intersection(preprocessor_deps_opts):
            return True

        if self.name == "CC" and self.conf.get("CC.ignore_cc1", True) and "-cc1" in cmd["opts"]:
            return True

        return False
