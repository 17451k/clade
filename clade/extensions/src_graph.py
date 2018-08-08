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

import sys

from clade.extensions.abstract import Extension
from clade.extensions.common import parse_args
from clade.extensions.utils import normalize_path
from clade.cmds import get_build_cwd


class SrcGraph(Extension):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        self.requires = ["CmdGraph", "CC"]

        self.out_list = []
        self.src_graph = dict()
        self.src_graph_file = "src_graph.json"

        super().__init__(work_dir, conf)

    def load_src_graph(self):
        """Load source graph."""
        return self.load_data(self.src_graph_file)

    def parse(self, cmds):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds)

        self.__generate_src_graph(cmds)

    def __generate_src_graph(self, cmds):
        try:
            cmd_graph = self.extensions["CmdGraph"].load_cmd_graph()
        except FileNotFoundError:
            return

        self.log("Start source graph constructing")

        build_cwd = get_build_cwd(cmds)

        for cmd in self.extensions["CC"].load_all_cmds():
            if not cmd["out"] or not cmd["in"] or cmd["in"][0] == "/dev/null" or cmd["in"][0] == "-":
                continue

            cmd_id = str(cmd["id"])

            # used_by is a list of commands that use (possibly indirectly) output of the command with ID=cmd_id
            used_by = self.__find_used_by(cmd_graph, cmd_id)

            for src_file in self.extensions["CC"].load_deps_by_id(cmd_id):
                rel_in = normalize_path(src_file, build_cwd)

                if rel_in not in self.src_graph:
                    self.src_graph[rel_in] = self.__get_new_value()

                # compiled_in is a list of commands that compile 'rel_in' source file
                self.src_graph[rel_in]["compiled_in"].add(cmd_id)
                self.src_graph[rel_in]["used_by"].update(used_by)

        if self.src_graph:
            self.dump_data(self.src_graph, self.src_graph_file)

        self.log("Constructing finished")

    def __find_used_by(self, cmd_graph, cmd_id):
        used_by = set()

        for used_by_id in cmd_graph[cmd_id]["used_by"]:
            used_by.add(used_by_id)
            used_by.update(self.__find_used_by(cmd_graph, used_by_id))

        return used_by

    @staticmethod
    def __get_new_value():
        return {
            "compiled_in": set(),
            "used_by": set()
        }


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = SrcGraph(args.work_dir, conf={"log_level": args.log_level})
    c.parse(args.cmds_file)
