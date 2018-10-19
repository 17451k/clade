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
import sys

from clade.extensions.abstract import Extension
from clade.extensions.utils import common_main, normalize_path


class SrcGraph(Extension):
    requires = ["CmdGraph", "CC"]

    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        self.src_graph = dict()
        self.src_graph_file = "src_graph.json"

    def load_src_graph(self):
        """Load source graph."""
        return self.load_data(self.src_graph_file)

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Start source graph constructing")

        self.__generate_src_graph(cmds_file)
        self.dump_data(self.src_graph, self.src_graph_file)

        if not self.src_graph:
            self.warning("Source graph is empty")

        self.log("Constructing finished")

    def __generate_src_graph(self, cmds_file):
        try:
            cmd_graph = self.extensions["CmdGraph"].load_cmd_graph()
        except FileNotFoundError:
            return

        src = self.get_build_cwd(cmds_file)

        for cmd in self.extensions["CmdGraph"].load_all_cmds_by_type("CC"):
            if not self.extensions["CC"].is_a_compilation_command(cmd):
                continue

            cmd_id = str(cmd["id"])

            # used_by is a list of commands that use (possibly indirectly) output of the command with ID=cmd_id
            used_by = self.__find_used_by(cmd_graph, cmd_id)

            for src_file in self.extensions["CC"].load_deps_by_id(cmd_id):
                rel_in = normalize_path(src_file, cmd["cwd"], src)

                if rel_in not in self.src_graph:
                    self.src_graph[rel_in] = self.__get_new_value()
                    self.src_graph[rel_in]["loc"] = self.__estimate_loc_size(os.path.join(src, rel_in))

                # compiled_in is a list of commands that compile 'rel_in' source file
                self.src_graph[rel_in]["compiled_in"].add(cmd_id)
                self.src_graph[rel_in]["used_by"].update(used_by)

    def __find_used_by(self, cmd_graph, cmd_id):
        used_by = set()

        for used_by_id in cmd_graph[cmd_id]["used_by"]:
            used_by.add(used_by_id)
            used_by.update(self.__find_used_by(cmd_graph, used_by_id))

        return used_by

    def __estimate_loc_size(self, file):
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
        return {
            "compiled_in": set(),
            "used_by": set()
        }


def main(args=sys.argv[1:]):
    common_main(SrcGraph, args)
