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
from clade.extensions.common import parse_args


class CmdGraph(Extension):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        if "requires" not in conf:
            self.requires = ["CC", "LD", "MV", "Objcopy"]
        else:
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
        graph = self.graph
        get_new_val = self.__get_new_value
        out_dict = self.out_dict

        out_id = str(cmd["id"])
        if out_id not in graph:
            graph[out_id] = get_new_val()
            graph[out_id]["type"] = ext_name

        for cmd_in in (i for i in cmd["in"] if i in out_dict):
            in_id = out_dict[cmd_in]
            graph[in_id]["used_by"].append(out_id)
            graph[out_id]["using"].append(in_id)

        # It rewrites values to keep the latest command
        out_dict[cmd["out"]] = out_id

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
    def __get_new_value():
        return {
            "used_by": list(),
            "using": list(),
            "type": None
        }


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = CmdGraph(args.work_dir, conf={"log_level": args.log_level})
    c.parse(args.cmds_file)
