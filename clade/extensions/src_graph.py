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

import hashlib
import os
import sys

from clade.extensions.abstract import Extension
from clade.extensions.utils import common_main, merge_preset_to_conf


class SrcGraph(Extension):
    __version__ = "1"

    always_requires = ["CmdGraph", "Path"]
    requires = always_requires + ["CC", "CL"]

    def __init__(self, work_dir, conf=None, preset="base"):
        conf = conf if conf else dict()
        conf = merge_preset_to_conf(preset, conf)

        if "SrcGraph.requires" in conf:
            self.requires = self.always_requires + conf["SrcGraph.requires"]

        super().__init__(work_dir, conf, preset)

        self.src_graph = dict()
        self.src_graph_file = "src_graph.json"
        self.src_graph_folder = "src_graph"

        self.src_info = dict()
        self.src_info_file = "src_info.json"

    def load_src_graph(self, files=None):
        """Load source graph."""
        if files:
            return self.load_data_by_key(self.src_graph_folder, files)
        else:
            return self.load_data(self.src_graph_file)

    def load_src_info(self):
        """Load information about source files."""
        return self.load_data(self.src_info_file)

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing {} commands".format(len(list(self.load_all_cmds()))))

        cmds_iter = self.load_all_cmds()
        self.__generate_src_graph(cmds_iter)
        self.dump_data(self.src_graph, self.src_graph_file)
        self.dump_data(self.src_info, self.src_info_file)
        self.dump_data_by_key(self.src_graph, self.src_graph_folder)

        if not self.src_graph:
            self.warning("Source graph is empty")

        self.src_graph.clear()

    def load_all_cmds(self):
        cmds = []

        for ext_name in [
            x for x in self.extensions if x not in self.always_requires
        ]:
            for cmd in self.extensions[ext_name].load_all_cmds(
                compile_only=True
            ):
                cmd["type"] = ext_name
                cmds.append(cmd)

        return cmds

    def __generate_src_graph(self, cmds):
        try:
            cmd_graph = self.extensions["CmdGraph"].load_cmd_graph()
        except FileNotFoundError:
            return

        for cmd in cmds:
            cmd_id = str(cmd["id"])
            cmd_type = cmd["type"]

            # used_by is a list of commands that use (possibly indirectly)
            # output of the command with ID=cmd_id
            used_by = self.__find_used_by(cmd_graph, cmd_id)

            for src_file in self.extensions[cmd_type].load_deps_by_id(cmd_id):
                norm_in = self.extensions["Path"].get_rel_path(
                    src_file, cmd["cwd"]
                )

                if norm_in not in self.src_graph:
                    self.src_graph[norm_in] = self.__get_new_value()

                    abs_src_file = os.path.join(cmd["cwd"], src_file)
                    self.src_info[norm_in] = {
                        "loc": self.__count_file_loc(abs_src_file),
                    }

                # compiled_in is a list of commands
                # that compile 'rel_in' source file
                self.src_graph[norm_in]["compiled_in"].add(cmd_id)
                self.src_graph[norm_in]["used_by"].update(used_by)

    def __find_used_by(self, cmd_graph, cmd_id):
        used_by = set()

        for used_by_id in cmd_graph[cmd_id]["used_by"]:
            used_by.add(used_by_id)
            used_by.update(self.__find_used_by(cmd_graph, used_by_id))

        return used_by

    def __count_file_loc(self, file):
        """Count number of lines of code in the file."""
        try:
            with open(file, "rb") as f:
                for i, _ in enumerate(f):
                    pass
            return i + 1
        except UnboundLocalError:
            # File is empty
            return 0
        except FileNotFoundError:
            self.warning("Cannot get size of file {}".format(file))
            return 0

    @staticmethod
    def __get_new_value():
        return {"compiled_in": set(), "used_by": set()}


def main(args=sys.argv[1:]):
    common_main(SrcGraph, args)
