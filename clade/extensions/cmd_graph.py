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

from graphviz import Digraph

from clade.extensions.abstract import Extension
from clade.extensions.utils import parse_args


class CmdGraph(Extension):
    requires = ["CC", "LD", "MV", "Objcopy"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        if "requires" in conf:
            self.requires = conf["requires"]

        self.graph = dict()
        self.out_dict = dict()
        self.graph_file = "cmd_graph.json"
        self.graph_dot = "cmd_graph.dot"

        super().__init__(work_dir, conf)

    def load_cmd_graph(self):
        """Load command graph."""
        return self.load_data(self.graph_file)

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)

        self.log("Start command graph constructing")
        parsed_cmds = list()
        for ext_name in self.extensions:
            parsed_cmds.extend([(x, ext_name) for x in self.extensions[ext_name].load_all_cmds()])

        for parsed_cmd, ext_name in sorted(parsed_cmds, key=lambda x: x[0]["id"]):
            self.__add_to_graph(parsed_cmd, ext_name)

        if self.graph:
            self.dump_data(self.graph, self.graph_file)

            if self.conf.get("CmdGraph.as_picture"):
                self.__print_source_graph()

        self.log("Constructing finished")

    def __add_to_graph(self, cmd, ext_name):
        out_id = str(cmd["id"])
        if out_id not in self.graph:
            self.graph[out_id] = self.__get_new_value(ext_name)

        for cmd_in in (i for i in cmd["in"] if i in self.out_dict):
            in_id = self.out_dict[cmd_in]
            self.graph[in_id]["used_by"].append(out_id)
            self.graph[out_id]["using"].append(in_id)

        # Rewrite cmd["out"] value to keep the latest used command id
        self.out_dict[cmd["out"]] = out_id

    def __print_source_graph(self):
        dot = Digraph(graph_attr={'rankdir': 'LR'}, node_attr={'shape': 'rectangle'})

        added_nodes = dict()

        graph = self.graph
        for cmd_id in graph:
            cmd_type = graph[cmd_id]["type"]
            cmd = self.extensions[cmd_type].load_json_by_id(cmd_id)

            if not cmd["out"]:
                continue

            if cmd["out"] not in added_nodes:
                dot.node(cmd["out"])
                added_nodes[cmd["out"]] = 1

            for cmd_in in cmd["in"]:
                if cmd_in not in added_nodes:
                    dot.node(cmd_in)
                    added_nodes[cmd_in] = 1
                dot.edge(cmd_in, cmd["out"], label="{}({})".format(cmd_type, cmd_id))

        dot.render(self.graph_dot)

    @staticmethod
    def __get_new_value(cmd_type):
        return {
            "used_by": list(),
            "using": list(),
            "type": cmd_type
        }


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = CmdGraph(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
